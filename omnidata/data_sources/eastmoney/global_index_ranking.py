"""
东方财富全球指数涨跌排行 Spider
获取全球主要指数的实时涨跌幅排行榜数据

从 https://quote.eastmoney.com/center/gridlist.html#global_asia 入口页面加载，
通过浏览器原生请求访问 https://push2.eastmoney.com/weblogin/api/qt/clist/get，
服务端看到的是带 cookie / referer / sec-ch-ua 等真实浏览器指纹的请求，
反爬风险最低。
"""

import json
import re
from datetime import datetime
from typing import Literal

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


# 热门全球指数代码清单（覆盖美股/港股/亚太/欧洲/其他主要市场）
# 不同地区使用的市场前缀不同：沪深指数用 m:i 前缀（1=沪市、0=深市），海外指数用 100/124 等市场ID
# i:1.000001 上证指数, i:0.399001 深证成指, i:0.399005 中小100, i:0.399006 创业板指, i:1.000300 沪深300
# i:124.HSCCI 港股红筹指数（港股使用124市场前缀）, i:100.HSI/i:100.HSCEI/i:100.TWII 等其他海外指数
GLOBAL_INDICES = {
    # 沪深指数
    "000001": "上证指数",
    "399001": "深证成指",
    "399005": "中小100",
    "399006": "创业板指",
    "000300": "沪深300",
    # 美股
    "DJI": "道琼斯",
    "SPX": "标普500",
    "IXIC": "纳斯达克综合",
    "NDX": "纳斯达克100",
    "RUI": "罗素2000",
    "SOX": "费城半导体",
    # 港股
    "HSI": "恒生指数",
    "HSCEI": "恒生中国企业指数",
    "HSTECH": "恒生科技指数",
    "HSCCI": "红筹指数",
    # 亚太
    "TWII": "台湾加权",
    "N225": "日经225",
    "KOSPI200": "韩国KOSPI200",
    "KS11": "韩国KOSPI",
    "STI": "新加坡海峡时报",
    "SENSEX": "印度孟买SENSEX",
    "KLSE": "马来西亚吉隆坡综指",
    "SET": "泰国SET",
    "PSI": "菲律宾综合",
    "KSE100": "巴基斯坦卡拉奇100",
    "VNINDEX": "越南胡志明",
    "JKSE": "印尼雅加达综合",
    "CSEALL": "斯里兰卡科伦坡",
    # 欧洲
    "SX5E": "欧洲斯托克50",
    "FTSE": "英国富时100",
    "MCX": "英国富时250",
    "GDAXI": "德国DAX30",
    "FCHI": "法国CAC40",
    "AEX": "荷兰AEX",
    "IBEX": "西班牙IBEX35",
    "FTSEMIB": "意大利富时MIB",
    "PSI20": "葡萄牙PSI20",
    "OMXC20": "丹麦OMXC20",
    "OMXSPI": "瑞典OMXSPI",
    "SSMI": "瑞士SMI",
    "ATX": "奥地利ATX",
    "BEL20": "比利时BEL20",
    "HEX": "芬兰赫尔辛基",
    "OSEBX": "挪威OSEBX",
    "WIG20": "波兰WIG20",
    "RTS": "俄罗斯RTS",
    "MOEX": "莫斯科交易所",
    # 美洲其他
    "BVSP": "巴西BOVESPA",
    "MXX": "墨西哥BOLSA",
    "IPSA": "智利IPSA",
    "MERV": "阿根廷MERVAL",
    "GSPTSE": "加拿大S&P/TSX",
    # 其他
    "TA35": "以色列TA35",
    "TASI": "沙特TASI",
    "DFMGI": "迪拜DFM",
}


# 不同指数代码对应的 fs 前缀（用于构建 fs 参数）
# 沪深指数使用 m:i 前缀（1=沪市、0=深市）
# 港股 HSCCI 使用 124 市场前缀，其他港股使用 100
# 其余海外指数使用 100 市场前缀
def _build_index_fs(code: str) -> str:
    """根据指数代码构建 fs 参数中的 i:XXX.YYY 片段"""
    # 沪深指数：沪市(1) / 深市(0)
    if code in ("000001", "000300"):
        return f"i:1.{code}"
    if code in ("399001", "399005", "399006"):
        return f"i:0.{code}"
    # 港股 HSCCI 使用 124 市场前缀
    if code == "HSCCI":
        return f"i:124.{code}"
    # 其他海外指数使用 100 市场前缀
    return f"i:100.{code}"


class GlobalIndexRankingParams(BaseModel):
    """全球指数涨跌排行参数模型"""

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=50, ge=1, le=100, description="每页数量，最大100")
    sort_field: Literal["f3", "f2", "f4", "f7", "f12"] = Field(
        default="f3",
        description=(
            "排序字段，"
            "f3=涨跌幅, "
            "f2=最新点位, "
            "f4=涨跌点位, "
            "f7=振幅, "
            "f12=指数代码"
        ),
    )
    sort_order: Literal["desc", "asc"] = Field(
        default="desc", description="排序方向，desc=降序, asc=升序"
    )
    region: Literal["all", "cn", "us", "hk", "asia", "europe", "americas"] = Field(
        default="all",
        description=(
            "市场筛选："
            "all=全部, "
            "cn=沪深A股, "
            "us=美股, "
            "hk=港股, "
            "asia=亚太, "
            "europe=欧洲, "
            "americas=美洲其他"
        ),
    )


class GlobalIndexRankingSpider(BaseWebSpider):
    """
    全球指数涨跌排行 Spider

    从东方财富网获取全球主要指数的实时行情排行榜数据
    包括指数代码、名称、最新点位、涨跌幅、涨跌点位、振幅、最高、最低、今开、昨收等数据
    支持分页查询、多种排序方式以及地区筛选
    """

    name = "eastmoney_global_index_ranking"
    description = "获取全球主要指数涨跌幅排行数据，支持分页、排序和地区筛选（美股/港股/亚太/欧洲）"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = GlobalIndexRankingParams

    # API 配置（使用 weblogin 接口路径，对应入口页面的登录态请求）
    API_URL = "https://push2.eastmoney.com/weblogin/api/qt/clist/get"
    DEFAULT_UT = "fa5fd1943c7b386f172d6893dbfba10b"

    # 地区筛选：指数代码清单
    REGION_FILTERS = {
        "cn": ["000001", "399001", "399005", "399006", "000300"],
        "us": ["DJI", "SPX", "IXIC", "NDX", "RUI", "SOX"],
        "hk": ["HSI", "HSCEI", "HSTECH", "HSCCI"],
        "asia": [
            "TWII", "N225", "KOSPI200", "KS11", "STI", "SENSEX",
            "KLSE", "SET", "PSI", "KSE100", "VNINDEX", "JKSE", "CSEALL",
        ],
        "europe": [
            "SX5E", "FTSE", "MCX", "GDAXI", "FCHI", "AEX",
            "IBEX", "FTSEMIB", "PSI20", "OMXC20", "OMXSPI",
            "SSMI", "ATX", "BEL20", "HEX", "OSEBX", "WIG20",
            "RTS", "MOEX",
        ],
        "americas": ["BVSP", "MXX", "IPSA", "MERV", "GSPTSE"],
    }

    # 请求字段（包含行情所需的全部字段）
    FIELDS = "f12,f13,f14,f292,f1,f2,f4,f3,f152,f17,f18,f15,f16,f7,f124"

    # 入口页面：用于动态提取 ut 令牌
    ENTRY_URL = "https://quote.eastmoney.com/center/gridlist.html#global_asia"

    async def crawl(self, params: GlobalIndexRankingParams) -> SpiderResult:
        """
        爬取全球指数涨跌排行数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # ── 动态提取 ut 令牌：拦截入口页面加载时自身发起的 push2 API 请求 ──
                captured_ut = {}

                async def capture_ut(route):
                    m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                    if m:
                        captured_ut["token"] = m.group(1)
                    await route.continue_()

                await page.route("**push2.eastmoney.com**", capture_ut)

                await page.goto(self.ENTRY_URL)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程
                    pass

                ut = captured_ut.get("token") or self.DEFAULT_UT

                # 构建 fs 参数（全球指数代码列表）
                fs = self._build_fs(params.region)

                # 构建请求参数
                request_params = {
                    "np": "1",
                    "fltt": "1",
                    "invt": "2",
                    "fs": fs,
                    "fields": self.FIELDS,
                    "fid": params.sort_field,
                    "pn": str(params.page),
                    "pz": str(params.page_size),
                    "po": "1" if params.sort_order == "desc" else "0",
                    "dect": "1",
                    "ut": ut,
                    "wbp2u": "|0|0|0|web",
                }

                response_text = await page.evaluate(
                    """
                    async ([apiUrl, params]) => {
                        const url = new URL(apiUrl);
                        Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
                        const resp = await fetch(url.toString(), { credentials: 'include' });
                        if (!resp.ok) return null;
                        return await resp.text();
                    }
                    """,
                    [self.API_URL, request_params],
                )

                if response_text is None:
                    return SpiderResult(success=False, message="请求失败")

                # 尝试解析JSONP响应（去除jQuery回调函数）
                json_match = re.search(r"\((.*)\)$", response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    try:
                        data = json.loads(response_text)
                    except json.JSONDecodeError:
                        return SpiderResult(
                            success=False,
                            message=f"响应格式错误，无法解析: {response_text[:200]}",
                        )

                # 检查返回状态
                if data.get("rc") != 0:
                    return SpiderResult(
                        success=False, message=f"获取数据失败：{data.get('msg', '未知错误')}"
                    )

                data_obj = data.get("data", {})
                if not data_obj:
                    return SpiderResult(success=False, message="未获取到数据")

                total = data_obj.get("total", 0)
                diff_list = data_obj.get("diff", [])

                if not diff_list:
                    return SpiderResult(
                        success=True,
                        data={
                            "total": total,
                            "indices": [],
                            "page": params.page,
                            "page_size": params.page_size,
                            "region": params.region,
                            "sort_field": params.sort_field,
                            "sort_order": params.sort_order,
                        },
                        message="当前页无数据",
                    )

                # 解析指数列表
                indices = [self._parse_index(item) for item in diff_list]

                return SpiderResult(
                    success=True,
                    data={
                        "total": total,
                        "indices": indices,
                        "page": params.page,
                        "page_size": params.page_size,
                        "region": params.region,
                        "sort_field": params.sort_field,
                        "sort_order": params.sort_order,
                    },
                    message=f"成功获取第{params.page}页全球指数排行，共{len(indices)}条",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _build_fs(self, region: str) -> str:
        """
        构建 fs 参数（指数代码列表，逗号分隔，每个前加 i:XXX.）

        Args:
            region: 地区标识

        Returns:
            fs 参数字符串
        """
        if region == "all":
            codes = list(GLOBAL_INDICES.keys())
        else:
            codes = self.REGION_FILTERS.get(region, [])
        return ",".join(_build_index_fs(code) for code in codes)

    def _parse_index(self, item: dict) -> dict:
        """
        解析单个指数数据

        Args:
            item: API返回的单条数据

        Returns:
            解析后的数据字典
        """

        def safe_float(value) -> float:
            """安全地将值转换为 float"""
            if value is None or value == "" or value == "-":
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0

        def safe_int(value) -> int:
            """安全地将值转换为 int"""
            if value is None or value == "" or value == "-":
                return 0
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0

        def safe_str(value) -> str:
            """安全地将值转换为 str"""
            if value is None or value == "-":
                return ""
            return str(value)

        # 字段映射：
        # f1: 市场类型(2=全球指数)
        # f2: 最新点位
        # f3: 涨跌幅(万分位)
        # f4: 涨跌点位
        # f7: 振幅(万分位)
        # f12: 指数代码
        # f13: 市场ID(100=全球指数)
        # f14: 指数名称
        # f15: 最高点位
        # f16: 最低点位
        # f17: 今开点位
        # f18: 昨收点位
        # f124: 时间戳
        # f152: 小数位数(用于还原精确数值)
        # f292: 市场类型标识(5=港股/欧美等海外指数)

        # 根据 f152 还原实际数值（点位 = 原值 / 10^f152）
        # 注意：f152 是字符串 "2"，表示该指数保留2位小数
        # API返回的原始点位已经乘以了 10^f152
        precision = safe_int(item.get("f152"))
        if precision < 0:
            precision = 0
        if precision > 6:
            precision = 6
        divisor = 10**precision

        code = safe_str(item.get("f12"))
        name = safe_str(item.get("f14")) or GLOBAL_INDICES.get(code, code)

        update_ts = safe_int(item.get("f124"))
        update_time = (
            datetime.fromtimestamp(update_ts).strftime("%Y-%m-%d %H:%M:%S")
            if update_ts
            else ""
        )

        result = {
            "代码": code,
            "名称": name,
            "最新点位": round(safe_float(item.get("f2")) / divisor, precision),
            "涨跌幅(%)": round(safe_float(item.get("f3")) / 100, 2),
            "涨跌点位": round(safe_float(item.get("f4")) / divisor, precision),
            "振幅(%)": round(safe_float(item.get("f7")) / 100, 2),
            "今开": round(safe_float(item.get("f17")) / divisor, precision),
            "昨收": round(safe_float(item.get("f18")) / divisor, precision),
            "最高": round(safe_float(item.get("f15")) / divisor, precision),
            "最低": round(safe_float(item.get("f16")) / divisor, precision),
            "更新时间": update_time,
        }

        return result