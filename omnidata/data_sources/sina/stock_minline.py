"""
新浪财经个股分时 Spider
获取个股指定交易日的分时数据（分钟级 价格 / 均价 / 成交量）

数据来源：新浪财经 realstock 历史分时月度文件
    https://finance.sina.com.cn/realstock/company/{symbol}/hisdata/{yyyy}/{mm}.js?d={date}
该月度文件覆盖任意历史交易日（实测回溯至 2020 年仍可用），每月一个文件、含当月全部
交易日分时数据；但返回内容经过压缩混淆，需用新浪 sf_sdk.js（utils.util 模块的
xh5_S_KLC_D 函数）在浏览器上下文内解码。解码函数为自包含纯函数，已内嵌于本文件，
经 `page.evaluate` 在浏览器内执行（确定性复用新浪官方解码算法，不依赖外部 SDK）。

分时时间轴共 241 个交易分钟，随新浪历史编码分两种版本：
- 现行格式：上午 09:30–11:30（121 分钟）+ 下午 13:01–15:00（120 分钟）
- 早期格式：上午 09:30–11:29（120 分钟）+ 下午 13:00–15:00（121 分钟）

解码后的每日数据为 242 行，含一行午间过渡的填充行（成交量 0、价格与前一分钟相同），
填充行位于索引 121（现行格式）或 120（早期格式）。爬虫按成交量 0 自动检测填充行并
剔除，再按对应版本时间轴逐分钟打标；两种版本均还原为 241 个真实交易分钟。

免登录、免 API Key。成交量单位与新浪分时口径一致（沪深个股为股，指数/基金为手）。
"""

import logging
import re
from datetime import datetime
from typing import Any, Literal

import pandas as pd
from playwright.async_api import Page
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult

logger = logging.getLogger(__name__)

# 现行格式时间轴：09:30–11:30（121）+ 13:01–15:00（120）= 241
_MODERN_TIMES = [
    f"{h:02d}:{m:02d}"
    for h in range(9, 16)
    for m in range(60)
    if 570 <= h * 60 + m <= 690 or 781 <= h * 60 + m <= 900
]

# 早期格式时间轴：09:30–11:29（120）+ 13:00–15:00（121）= 241
_LEGACY_TIMES = [
    f"{h:02d}:{m:02d}"
    for h in range(9, 16)
    for m in range(60)
    if 570 <= h * 60 + m <= 689 or 780 <= h * 60 + m <= 900
]

# 新浪 sf_sdk.js `utils.util.xh5_S_KLC_D` 解码函数（自包含纯函数）。
# 用于解码 hisdata 月度分时文件的压缩数据；若新浪升级编码方案需同步更新此常量。
_HISDATA_DECODER = """function(t){var e,n,o,i,r,a,s,l=(arguments,864e5),u=7657,c=[],h=[],d=~(3<<30),f=1<<30,p=[0,3,5,6,9,10,12,15,17,18,20,23,24,27,29,30],g=Math,v=function(){var l,u;for(l=0;64>l;l++)h[l]=g.pow(2,l),26>l&&(c[l]=m(l+65),c[l+26]=m(l+97),10>l&&(c[l+52]=m(l+48)));for(c.push("+","/"),c=c.join(""),n=t.split(""),o=n.length,l=0;o>l;l++)n[l]=c.indexOf(n[l]);return i={},e=a=0,r={},u=w([12,6]),s=63^u[1],{_1479:H,_136:C,_200:A,_139:L,_197:F,_3466:I}["_"+u[0]]||function(){return[]}},m=String.fromCharCode,b=function(t){return t==={}._},y=function(){var t,e;for(t=x(),e=1;;){if(!x())return e*(2*t-1);e++}},x=function(){var t;return e>=o?0:(t=n[e]&1<<a,a++,a>=6&&(a-=6,e++),!!t)},w=function(t,i,r){var s,l,u,c,d;for(l=[],u=0,i||(i=[]),r||(r=[]),s=0;s<t.length;s++)if(c=t[s],u=0,c){if(e>=o)return l;if(t[s]<=0)u=0;else if(t[s]<=30){for(;d=6-a,d=c>d?d:c,u|=(n[e]>>a&(1<<d)-1)<<t[s]-c,a+=d,a>=6&&(a-=6,e++),c-=d,!(0>=c););i[s]&&u>=h[t[s]-1]&&(u-=h[t[s]])}else u=w([30,t[s]-30],[0,i[s]]),r[s]||(u=u[0]+u[1]*h[30]);l[s]=u}else l[s]=0;return l},N=function(){var t;return t=w([3])[0],1==t?(i.d=w([18],[1])[0],t=0):t||(t=w([6])[0]),t},S=function(t){var e,n,o;for(t>1&&(e=0),e=0;t>e;e++)i.d++,o=i.d%7,(3==o||4==o)&&(i.d+=5-o);return n=new Date,n.setTime((u+i.d)*l),n},R=function(t){var e,n,o;for(o=i.wd||62,e=0;t>e;e++)do i.d++;while(!(o&1<<(i.d%7+10)%7));return n=new Date,n.setTime((u+i.d)*l),n},k=function(t){var e,n,o;return t?0>t?(e=k(-t),[-e[0],-e[1]]):(e=t%3,n=(t-e)/3,o=[n,n],e&&o[e-1]++,o):[0,0]},E=function(t,e,n){var o,i,r;for(i="number"==typeof e?k(e):e,r=k(n),o=[r[0]-i[0],r[1]-i[1]],i=1;o[0]<o[1];)i*=5,o[1]--;for(;o[1]<o[0];)i*=2,o[0]--;if(i>1&&(t*=i),o=o[0],t=D(t),0>o){for(;t.length+o<=0;)t="0"+t;return o+=t.length,i=t.substr(0,o)-0,void 0===n?i+"."+t.substr(o)-0:(r=t.charAt(o)-0,r>5?i++:5==r&&(t.substr(o+1)-0>0?i++:i+=1&i),i)}for(;o>0;o--)t+="0";return t-0},A=function(){var t,n,r,a,l;if(s>=1)return[];for(i.d=w([18],[1])[0]-1,r=w([3,3,30,6]),i.p=r[0],i.ld=r[1],i.cd=r[2],i.c=r[3],i.m=g.pow(10,i.p),i.pc=i.cd/i.m,n=[],t=0;a={d:1},x()&&(r=w([3])[0],0==r?a.d=w([6])[0]:1==r?(i.d=w([18])[0],a.d=0):a.d=r),l={date:S(a.d)},x()&&(i.ld+=y()),r=w([3*i.ld],[1]),i.cd+=r[0],l.close=i.cd/i.m,n.push(l),!(e>=o)&&(e!=o-1||63&(i.c^t+1));t++);return n[0].prevclose=i.pc,n},C=function(){var t,n,r,a,l,u,c,h,d,f,p;if(s>2)return[];for(c=[],d={v:"volume",p:"price",a:"avg_price"},i.d=w([18],[1])[0]-1,h={date:S(1)},r=w(1>s?[3,3,4,1,1,1,5]:[4,4,4,1,1,1,3]),t=0;7>t;t++)i[["la","lp","lv","tv","rv","zv","pp"][t]]=r[t];for(i.m=g.pow(10,i.pp),s>=1?(r=w([3,3]),i.c=r[0],r=r[1]):(r=5,i.c=2),i.pc=w([6*r])[0],h.pc=i.pc/i.m,i.cp=i.pc,i.da=0,i.sa=i.sv=0,t=0;!(e>=o)&&(e!=o-1||7&(i.c^t));t++){for(l={},a={},f=i.tv?x():1,n=0;3>n;n++)if(p=["v","p","a"][n],(f?x():0)&&(r=y(),i["l"+p]+=r),u="v"==p&&i.rv?x():1,r=w([3*i["l"+p]+("v"==p?7*u:0)],[!!n])[0]*(u?1:100),a[p]=r,"v"==p){if(!(l[d[p]]=r)&&(s>1||241>t)&&(i.zv?!x():1)){a.p=0;break}}else"a"==p&&(i.da=(1>s?0:i.da)+a.a);i.sv+=a.v,l[d.p]=(i.cp+=a.p)/i.m,i.sa+=a.v*i.cp,l[d.a]=b(a.a)?t?c[t-1][d.a]:l[d.p]:i.sv?((g.floor((i.sa*(2e3/i.m)+i.sv)/i.sv)>>1)+i.da)/1e3:l[d.p]+i.da/1e3,c.push(l)}return c[0].date=h.date,c[0].prevclose=h.pc,c},H=function(){var t,e,n,o,r,a,l;if(s>=1)return[];for(i.lv=0,i.ld=0,i.cd=0,i.cv=[0,0],i.p=w([6])[0],i.d=w([18],[1])[0]-1,i.m=g.pow(10,i.p),r=w([3,3]),i.md=r[0],i.mv=r[1],t=[];r=w([6]),r.length;){if(n={c:r[0]},o={},n.d=1,32&n.c)for(;;){if(r=w([6])[0],63==(16|r)){l=16&r?"x":"u",r=w([3,3]),n[l+"_d"]=r[0]+i.md,n[l+"_v"]=r[1]+i.mv;break}if(32&r){a=8&r?"d":"v",l=16&r?"x":"u",n[l+"_"+a]=(7&r)+i["m"+a];break}if(a=15&r,0==a?n.d=w([6])[0]:1==a?(i.d=a=w([18])[0],n.d=0):n.d=a,!(16&r))break}o.date=S(n.d);for(a in{v:0,d:0})b(n["x_"+a])||(i["l"+a]=n["x_"+a]),b(n["u_"+a])&&(n["u_"+a]=i["l"+a]);for(n.l_l=[n.u_d,n.u_d,n.u_d,n.u_d,n.u_v],l=p[15&n.c],1&n.u_v&&(l=31-l),16&n.c&&(n.l_l[4]+=2),e=0;5>e;e++)l&1<<4-e&&n.l_l[e]++,n.l_l[e]*=3;n.d_v=w(n.l_l,[1,0,0,1,1],[0,0,0,0,1]),a=i.cd+n.d_v[0],o.open=a/i.m,o.high=(a+n.d_v[1])/i.m,o.low=(a-n.d_v[2])/i.m,o.close=(a+n.d_v[3])/i.m,r=n.d_v[4],"number"==typeof r&&(r=[r,r>=0?0:-1]),i.cd=a+n.d_v[3],l=i.cv[0]+r[0],i.cv=[l&d,i.cv[1]+r[1]+!!((i.cv[0]&d)+(r[0]&d)&f)],o.volume=(i.cv[0]&f-1)+i.cv[1]*f,t.push(o)}return t},L=function(){var t,e,n,o;if(s>1)return[];for(i.l=0,o=-1,i.d=w([18])[0]-1,n=w([18])[0];i.d<n;)e=S(1),0>=o?(x()&&(i.l+=y()),o=w([3*i.l],[0])[0]+1,t||(t=[e],o--)):t.push(e),o--;return t},F=function(){var t,n,r,a;if(s>=1)return[];for(i.f=w([6])[0],i.c=w([6])[0],r=[],i.dv=[],i.dl=[],t=0;t<i.f;t++)i.dv[t]=0,i.dl[t]=0;for(t=0;!(e>=o)&&(e!=o-1||7&(i.c^t));t++){for(a=[],n=0;n<i.f;n++)x()&&(i.dl[n]+=y()),i.dv[n]+=w([3*i.dl[n]],[1])[0],a[n]=i.dv[n];r.push(a)}return r},I=function(){if(i={b_avp:1,b_ph:0,b_phx:0,b_sep:0,p_p:6,p_v:0,p_a:0,p_e:0,p_t:0,l_o:3,l_h:3,l_l:3,l_c:3,l_v:5,l_a:5,l_e:3,l_t:0,u_p:0,u_v:0,u_a:0,wd:62,d:0},s>0)return[];var t,n,r,a,l,u,c;for(t=[];;){if(e>=o)return void 0;if(r={d:1,c:0},x())if(x()){if(x()){for(r.c++,r.a=i.b_avp,x()&&(i.b_avp^=x(),i.b_ph^=x(),i.b_phx^=x(),r.s=i.b_sep,i.b_sep^=x(),x()&&(i.wd=w([7])[0]),r.s^i.b_sep&&(r.s?i.u_p=i.u_c:i.u_o=i.u_h=i.u_l=i.u_c=i.u_p)),u=0;u<3+2*i.b_ph;u++)if(x()&&(l="pvaet".charAt(u),a=i["p_"+l],i["p_"+l]+=y(),i["u_"+l]=E(i["u_"+l],a,i["p_"+l])-0,i.b_sep&&!u))for(c=0;4>c;c++)l="ohlc".charAt(c),i["u_"+l]=E(i["u_"+l],a,i.p_p)-0;!i.b_avp&&r.a&&(i.u_a=E(n&&n.amount||0,0,i.p_a))}if(x())for(r.c++,u=0;u<7+i.b_ph+i.b_phx;u++)x()&&(6==u?r.d=N():i["l_"+"ohlcva*et".charAt(u)]+=y());if(x()&&(r.c++,l=i.l_o+(x()&&y()),a=w([3*l],[1])[0],r.p=i.b_sep?i.u_c+a:i.u_p+=a),!r.c)break}else x()?x()?x()?r.d=N():i.l_v+=y():i.b_ph&&x()?i["l_"+"et".charAt(i.b_phx&&x())]+=y():i.l_a+=y():i["l_"+"ohlc".charAt(w([2])[0])]+=y();for(u=0;u<6+i.b_ph+i.b_phx;u++)c="ohlcvaet".charAt(u),a=(i.b_sep?191:185)>>u&1,r["v_"+c]=w([3*i["l_"+c]],[a])[0];n={date:R(r.d)},r.p&&(n.prevclose=E(r.p,i.p_p)),i.b_sep?(n.open=E(i.u_o+=r.v_o,i.p_p),n.high=E(i.u_h+=r.v_h,i.p_p),n.low=E(i.u_l+=r.v_l,i.p_p),n.close=E(i.u_c+=r.v_c,i.p_p)):(r.o=i.u_p+r.v_o,n.open=E(r.o,i.p_p),n.high=E(r.o+r.v_h,i.p_p),n.low=E(r.o-r.v_l,i.p_p),n.close=E(i.u_p=r.o+r.v_c,i.p_p)),n.volume=E(i.u_v+=r.v_v,i.p_v),i.b_avp?(a=k(i.p_p),l=k(i.p_v),n.amount=E(E(Math.floor((i.b_sep?(i.u_o+i.u_h+i.u_l+i.u_c)/4:r.o+(r.v_h-r.v_l+r.v_c)/4)*i.u_v+.5),[a[0]+l[0],a[1]+l[1]],i.p_a)+r.v_a,i.p_a)):(i.u_a+=r.v_a,n.amount=E(i.u_a,i.p_a)),i.b_ph&&(n.postVol=E(r.v_e,i.p_e),n.postAmt=E(Math.floor(n.postVol*n.close+(i.b_phx?E(r.v_t,i.p_t):0)+.5),0)),t.push(n)}return t},D=function(t){var e,n,o;if(t=(t||0).toString(),o=[],n=t.toLowerCase().indexOf("e"),n>0){for(e=t.substr(n+1)-0;e>=0;e--)o.push(Math.floor(e*Math.pow(10,-e)+.5)-0);return o.join("")}return t};return v()()}"""

# 浏览器内解码脚本模板（`__DECODER__` 占位符在运行时替换为 _HISDATA_DECODER）
# 单次 evaluate 原子完成：注入解码函数 → 同源 fetch 月度文件 → 解码 → 返回结构化数据
_DECODE_SCRIPT = """async (url) => {
    const __dec = __DECODER__;
    const r = await fetch(url);
    if (!r.ok) return null;
    const text = await r.text();
    const m = text.match(/"([^"]*)"/);
    if (!m) return null;
    const parts = m[1].split(",");
    return parts.map(p => {
        const arr = __dec(p);
        const header = arr.shift();
        return {
            header: {
                date: header.date ? header.date.toISOString().slice(0, 10) : "",
                prev_close: header.prevclose
            },
            rows: arr.map(x => ({ price: x.price, avg_price: x.avg_price, volume: x.volume }))
        };
    });
}
"""


class StockMinlineParams(BaseModel):
    """个股分时参数模型"""

    symbol: str = Field(
        ...,
        min_length=6,
        max_length=10,
        description=(
            "证券标识，支持两种格式："
            "① 新浪前缀格式，如 'sh600519'(贵州茅台)、'sz000001'(平安银行)；"
            "② 裸 6 位代码自动推断市场：92/8/4 开头→北交所，6/5/9 开头→沪市，其余→深市"
        ),
    )
    date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="交易日，格式 YYYY-MM-DD，如 2026-08-13；可查询任意历史交易日",
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class StockMinlineSpider(BaseWebSpider):
    """
    新浪财经个股分时 Spider

    获取个股指定交易日的分时数据（分钟级价格 / 均价 / 成交量），可查询任意历史交易日
    （实测回溯至 2020 年仍可用）。分时时间轴按沪深 A 股标准：09:30–11:30、13:01–15:00。
    免登录、免 API Key；数据来自新浪 realstock 历史分时月度文件（压缩混淆），经浏览器
    上下文内嵌新浪官方解码函数在页面内还原。
    """

    name = "sina_stock_minline"
    description = (
        "获取个股/ETF指定交易日的分时数据（分钟级价格/均价/成交量），可查询任意历史交易日，"
    )
    version = "1.0.0"
    author = "noimank"
    platform = "新浪财经"

    params_model = StockMinlineParams

    # API 配置 - 新浪 realstock 历史分时月度文件
    HISDATA_BASE = "https://finance.sina.com.cn/realstock/company"
    # 暖手访问的新浪财经入口页：同源环境 + 累积 sina 域 cookie
    ENTRY_URL = "https://finance.sina.com.cn/"
    # 实时行情接口（仅用于取证券名称）
    QUOTE_API = "https://hq.sinajs.cn/list"
    REFERER = "https://finance.sina.com.cn/"
    # 入口页加载超时（毫秒）
    PAGE_TIMEOUT_MS = 15000
    # 名称请求超时（毫秒）
    REQUEST_TIMEOUT_MS = 8000

    async def crawl(self, params: StockMinlineParams) -> SpiderResult:
        """
        爬取个股指定交易日的分时数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        symbol = self._normalize_symbol(params.symbol)
        if symbol is None:
            return SpiderResult(
                success=False,
                message="无效的证券标识，请使用 sh600519/sz000001 格式或裸 6 位代码",
            )
        date_obj = self._parse_date(params.date)
        if date_obj is None:
            return SpiderResult(success=False, message="无效日期，请使用 YYYY-MM-DD 格式")
        date_str = date_obj.strftime("%Y-%m-%d")

        # 月度分时文件 URL：每月一个文件、含当月全部交易日，用 d 参数指定目标日期
        hisdata_url = (
            f"{self.HISDATA_BASE}/{symbol}/hisdata/"
            f"{date_obj.year}/{date_obj.month:02d}.js?d={date_str}"
        )

        async with self.new_page("sina") as page:
            await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

            # 先访问新浪财经首页：同源环境下 fetch 月度文件（真实用户访问链路 + 累积 cookie）。
            # 注：page.evaluate 内 fetch 走浏览器网络栈，加载失败不影响后续解码尝试
            try:
                await page.goto(
                    self.ENTRY_URL,
                    wait_until="domcontentloaded",
                    timeout=self.PAGE_TIMEOUT_MS,
                )
            except Exception:
                pass

            # 证券名称（可选元数据，失败不影响主流程）
            name = await self._fetch_name(page, symbol)

            # 浏览器内解码整个月度文件（单次 evaluate 原子完成）
            try:
                decoded = await page.evaluate(
                    _DECODE_SCRIPT.replace("__DECODER__", _HISDATA_DECODER),
                    hisdata_url,
                )
            except Exception as e:
                logger.warning("hisdata decode failed (%s): %s", hisdata_url, e)
                return SpiderResult(success=False, message="分时数据解码失败，请稍后重试")

            if not decoded:
                return SpiderResult(
                    success=False,
                    message=f"未获取到 {date_str} 所在月份的分时数据文件",
                )

            # 按目标日期筛选出当天分时（月度文件含当月全部交易日）
            day = next((d for d in decoded if d["header"].get("date") == date_str), None)
            if day is None:
                return SpiderResult(
                    success=False,
                    message=f"{date_str} 无分时数据（可能为非交易日或当日停牌）",
                )

            # 剔除午间填充行并逐分钟打时间标签（时间轴随历史格式自动适配）
            rows, times = self._clean_rows(day["rows"])
            if not rows:
                return SpiderResult(success=False, message=f"{date_str} 分时数据为空")

            minutes = [
                {
                    "时间": times[idx] if idx < len(times) else "",
                    "价格": row["price"],
                    "均价": row["avg_price"],
                    "成交量": row["volume"],
                }
                for idx, row in enumerate(rows)
            ]

            code = symbol[2:]
            display_name = name or symbol
            summary = {
                "证券代码": code,
                "证券名称": display_name,
                "日期": date_str,
                "昨收": day["header"].get("prev_close"),
                "分钟数": len(minutes),
                "分时": minutes,
            }

            result_data: Any = summary
            if params.data_format in ("markdown", "string"):
                df = pd.DataFrame(minutes)
                result_data = (
                    df.to_markdown() if params.data_format == "markdown" else df.to_string()
                )

            return SpiderResult(
                success=True,
                data=result_data,
                message=(
                    f"成功获取 {display_name}({code}) {date_str} 分时数据共 {len(minutes)} 条"
                ),
            )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str | None:
        """
        将证券标识规范化为新浪符号（前缀 + 6 位代码）

        - 前缀格式（sh/sz/bj + 6 位代码）直接保留
        - 裸 6 位代码按前缀推断市场：
            92/8/4 开头 → 北交所(bj)；6/5/9 开头 → 沪市(sh)；其余 → 深市(sz)

        Args:
            symbol: 用户传入的证券标识

        Returns:
            规范化后的新浪符号；无效标识返回 None
        """
        normalized = symbol.strip().lower()
        if re.fullmatch(r"(sh|sz|bj)\d{6}", normalized):
            return normalized
        if re.fullmatch(r"\d{6}", normalized):
            if normalized.startswith(("92", "8", "4")):
                return f"bj{normalized}"
            if normalized.startswith(("6", "5", "9")):
                return f"sh{normalized}"
            return f"sz{normalized}"
        return None

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        """解析 YYYY-MM-DD 日期字符串；格式非法返回 None"""
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _clean_rows(rows: list[dict]) -> tuple[list[dict], list[str]]:
        """
        剔除午间过渡填充行并返回对应版本的时间轴

        解码后的每日数据为 242 行，含一行午间填充行（成交量 0、价格与前一分钟相同）。
        填充行在现行格式中位于索引 121（其后为 13:01 分钟），在早期格式中位于索引 120
        （其后为 13:00 分钟）。剔除填充行后剩 241 行，与对应版本时间轴逐分钟对齐。
        当日交易未过半时无填充行（或仅有上午全量 + 填充行），均按现行格式处理。

        Args:
            rows: 解码出的当日分时行列表

        Returns:
            (剔除填充行后的行列表, 对应版本的分时时间轴)
        """
        rows = [dict(row) for row in rows]
        legacy = False
        n = len(rows)
        if n == 242:
            # 完整交易日：现行格式填充行在 121，早期格式在 120（其 121 位置为 13:00 实数据）
            if rows[121].get("volume") == 0:
                rows.pop(121)
            elif rows[120].get("volume") == 0:
                rows.pop(120)
                legacy = True
        elif n >= 122 and rows[121].get("volume") == 0:
            # 当日盘中（现行格式）：已有上午全量 + 午间填充行，剔除填充行
            rows.pop(121)
        times = _LEGACY_TIMES if legacy else _MODERN_TIMES
        return rows, times

    async def _fetch_name(self, page: Page, symbol: str) -> str:
        """
        经浏览器上下文请求 hq.sinajs.cn 获取证券名称（GBK 解码），失败返回空串

        Args:
            page: Playwright Page 对象，使用其 request 走真实浏览器请求
            symbol: 新浪符号，如 sh600519

        Returns:
            证券名称；获取失败返回空串
        """
        url = f"{self.QUOTE_API}?list={symbol}"
        try:
            response = await page.request.get(
                url,
                headers={"Referer": self.REFERER},
                timeout=self.REQUEST_TIMEOUT_MS,
            )
            if response.status == 200:
                text = (await response.body()).decode("gbk", errors="replace")
                m = re.search(r'="([^,]*)', text)
                if m:
                    return m.group(1).strip()
        except Exception as e:
            logger.warning("fetch name failed for %s: %s", symbol, e)
        return ""
