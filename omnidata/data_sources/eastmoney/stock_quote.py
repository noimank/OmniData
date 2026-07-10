"""
东方财富网个股行情报价 Spider
获取个股或指数的实时行情报价数据

从 https://quote.eastmoney.com/ 页面获取数据
支持输入股票代码或指数代码查询实时行情
"""

import re
from datetime import datetime

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class StockQuoteParams(BaseModel):
    """个股行情报价参数模型"""

    stock_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="股票代码，6位数字，例如：000001(平安银行)、000002(万科A)、600000(浦发银行)",
    )


class StockQuoteSpider(BaseWebSpider):
    """
    个股行情报价 Spider

    从东方财富网获取个股或指数的实时行情报价数据
    包括最新价、涨跌幅、涨跌额、成交量、成交额、开盘价、收盘价、最高价、最低价、
    换手率、量比、市盈率、市净率、总市值、流通市值等完整行情数据
    """

    name = "eastmoney_stock_quote"
    description = "获取A股/ETF基金实时行情报价数据，包括最新价、涨跌幅、成交量、成交额、买卖五价、市值、市盈率等完整行情数据"
    version = "1.2.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockQuoteParams

    # API 配置 - 使用 /qt/stock/get 接口获取完整的买卖五价数据
    API_URL = "https://push2.eastmoney.com/api/qt/stock/get"
    DEFAULT_UT = "b2884a393a59ad64002292a3e90d46a5"
    # 请求字段：使用akshare的完整字段参数以确保获取买卖五价数据
    FIELDS = "f120,f121,f122,f174,f175,f59,f163,f43,f57,f58,f169,f170,f46,f44,f51,f168,f47,f164,f116,f60,f45,f52,f50,f48,f167,f117,f71,f161,f49,f530,f135,f136,f137,f138,f139,f141,f142,f144,f145,f147,f148,f140,f143,f146,f149,f55,f62,f162,f92,f173,f104,f105,f84,f85,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f107,f111,f86,f177,f78,f110,f262,f263,f264,f267,f268,f255,f256,f257,f258,f127,f199,f128,f198,f259,f260,f261,f171,f277,f278,f279,f288,f152,f250,f251,f252,f253,f254,f269,f270,f271,f272,f273,f274,f275,f276,f265,f266,f289,f290,f286,f285,f292,f293,f294,f295"

    async def crawl(self, params: StockQuoteParams) -> SpiderResult:
        """
        爬取个股行情报价数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # 根据股票代码自动判断市场ID
                # 6开头 = 上海市场(1), 0/3开头 = 深圳市场(0), 8开头 = 北交所(2)
                stock_code = params.stock_code
                if stock_code.startswith("6") or stock_code.startswith("5"):
                    market_id = "1"  # 上海
                # elif stock_code.startswith("8") or stock_code.startswith("9"):
                #     market_id = "2"  # 北交所
                else:
                    market_id = "0"  # 深圳

                secid = f"{market_id}.{stock_code}"

                # ── 动态提取 ut 令牌：拦截页面加载时自身发起的 push2 API 请求 ──
                captured_ut = {}

                async def capture_ut(route):
                    m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                    if m:
                        captured_ut["token"] = m.group(1)
                    await route.continue_()

                await page.route("**push2.eastmoney.com**", capture_ut)

                await page.goto("https://quote.eastmoney.com/")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程：ut 拿不到时会回退到 DEFAULT_UT
                    pass

                ut = captured_ut.get("token") or self.DEFAULT_UT

                # 构建请求参数
                request_params = {
                    "fltt": "2",
                    "invt": "2",
                    "fields": self.FIELDS,
                    "secid": secid,
                    "ut": ut,
                }

                result = await page.evaluate(
                    """
                    async ([apiUrl, params]) => {
                        const url = new URL(apiUrl);
                        Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
                        const resp = await fetch(url.toString(), { credentials: 'include' });
                        if (!resp.ok) return null;
                        return await resp.json();
                    }
                    """,
                    [self.API_URL, request_params],
                )

                if result is None:
                    return SpiderResult(success=False, message="请求失败")

                # 解析响应
                data = result

                # 检查返回状态
                if data.get("rc") != 0:
                    return SpiderResult(
                        success=False, message=f"获取数据失败：{data.get('msg', '未知错误')}"
                    )

                # 检查是否有数据 (新API直接返回data对象)
                quote_data = data.get("data", {})
                if not quote_data or not isinstance(quote_data, dict):
                    return SpiderResult(
                        success=False,
                        message=f"未找到股票代码 {params.stock_code} 的数据，请检查股票代码是否正确",
                    )

                # 解析数据
                result_data = self._parse_quote(quote_data)

                return SpiderResult(
                    success=True,
                    data=result_data,
                    message=f"成功获取 {params.stock_code} 的行情报价数据",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_quote(self, item: dict) -> dict:
        """
        解析行情报价数据

        Args:
            item: API返回的单条数据

        Returns:
            解析后的数据字典
        """

        def safe_float(value) -> float:
            """安全地将值转换为 float"""
            if value is None or value == "":
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0

        def safe_int(value) -> int:
            """安全地将值转换为 int"""
            if value is None or value == "":
                return 0
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0

        def safe_str(value) -> str:
            """安全地将值转换为 str"""
            if value is None:
                return ""
            return str(value)

        # 基础信息
        f57 = safe_str(item.get("f57"))  # 证券代码
        f58 = safe_str(item.get("f58"))  # 证券名称

        # 价格相关
        f43 = safe_float(item.get("f43"))  # 最新价
        f169 = safe_float(item.get("f169"))  # 涨跌额
        f170 = safe_float(item.get("f170"))  # 涨跌幅(%)
        f44 = safe_float(item.get("f60"))  # 昨收
        f45 = safe_float(item.get("f46"))  # 今开
        f46 = safe_float(item.get("f44"))  # 最高
        f60 = safe_float(item.get("f45"))  # 最低

        # 成交相关
        f47 = safe_int(item.get("f47"))  # 成交量(手)
        f48 = safe_float(item.get("f48"))  # 成交额(元)
        f49 = safe_int(item.get("f49"))  # 成交笔数

        # 买卖五价
        # 卖五到卖一（价格从高到低）
        f31 = safe_float(item.get("f31"))  # 卖五价
        f32 = safe_int(item.get("f32"))  # 卖五量
        f33 = safe_float(item.get("f33"))  # 卖四价
        f34 = safe_int(item.get("f34"))  # 卖四量
        f35 = safe_float(item.get("f35"))  # 卖三价
        f36 = safe_int(item.get("f36"))  # 卖三量
        f37 = safe_float(item.get("f37"))  # 卖二价
        f38 = safe_int(item.get("f38"))  # 卖二量
        f39 = safe_float(item.get("f39"))  # 卖一价
        f40 = safe_int(item.get("f40"))  # 卖一量

        # 买一到买五（价格从高到低）
        f19 = safe_float(item.get("f19"))  # 买一价
        f20 = safe_int(item.get("f20"))  # 买一量
        f17 = safe_float(item.get("f17"))  # 买二价
        f18 = safe_int(item.get("f18"))  # 买二量
        f15 = safe_float(item.get("f15"))  # 买三价
        f16 = safe_int(item.get("f16"))  # 买三量
        f13 = safe_float(item.get("f13"))  # 买四价
        f14 = safe_int(item.get("f14"))  # 买四量
        f11 = safe_float(item.get("f11"))  # 买五价
        f12 = safe_int(item.get("f12"))  # 买五量

        # 市值相关
        f116 = safe_float(item.get("f116"))  # 总市值(元)
        f117 = safe_float(item.get("f117"))  # 流通市值(元)
        f84 = safe_float(item.get("f84"))  # 总股本(股)
        f85 = safe_float(item.get("f85"))  # 流通股(股)

        # 市盈率/市净率
        f183 = safe_float(item.get("f183"))  # 总营收
        f184 = safe_float(item.get("f162"))  # 市盈率(动态)
        # f185 = safe_float(item.get("f185"))  # 市盈率(静态)
        f186 = safe_float(item.get("f167"))  # 市净率

        # 涨跌停
        f51 = safe_float(item.get("f51"))  # 涨停价
        f52 = safe_float(item.get("f52"))  # 跌停价

        # 行业板块
        f127 = safe_str(item.get("f127"))  # 所属行业
        f128 = safe_str(item.get("f128"))  # 所属板块

        # 更新时间
        f86 = safe_int(item.get("f86"))  # 更新时间戳
        update_time = datetime.fromtimestamp(f86).strftime("%Y-%m-%d %H:%M:%S") if f86 else ""

        # 构建返回数据
        result = {
            "证券代码": f57,
            "证券名称": f58,
            "最新价": round(f43, 2),
            "换手(%)": safe_float(item.get("f168")),
            "涨跌额": round(f169, 2),
            "涨跌幅": round(f170, 2),
            "今开": round(f45, 2),
            "昨收": round(f44, 2),
            "最高": round(f46, 2),
            "最低": round(f60, 2),
            "成交量(手)": f47,
            "成交额(万元)": round(f48 / 10000, 2),
            "成交笔数": f49,
            "总市值(亿元)": round(f116 / 100000000, 2),
            "流通市值(亿元)": round(f117 / 100000000, 2),
            "总股本(万股)": round(f84 / 10000, 2),
            "流通股(万股)": round(f85 / 10000, 2),
            "市盈率(动态)": round(f184, 2),
            # "市盈率(静态)": round(f185, 2),
            "市净率": round(f186, 2),
            "总营收(亿元)": round(f183 / 100000000, 2),
            "涨停价": round(f51, 2),
            "跌停价": round(f52, 2),
            "外盘(万元)": round(safe_float(item.get("f49")) / 10000, 2),
            "内盘(万元)": round(safe_float(item.get("f161")) / 10000, 2),
            "所属行业": f127,
            "所属板块": f128,
            "更新时间": update_time,
            "卖五": {"价格": round(f31, 2), "量": f32},
            "卖四": {"价格": round(f33, 2), "量": f34},
            "卖三": {"价格": round(f35, 2), "量": f36},
            "卖二": {"价格": round(f37, 2), "量": f38},
            "卖一": {"价格": round(f39, 2), "量": f40},
            "买一": {"价格": round(f19, 2), "量": f20},
            "买二": {"价格": round(f17, 2), "量": f18},
            "买三": {"价格": round(f15, 2), "量": f16},
            "买四": {"价格": round(f13, 2), "量": f14},
            "买五": {"价格": round(f11, 2), "量": f12},
        }

        return result
