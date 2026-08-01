"""
东方财富网沪深京A股列表 Spider
获取沪深京A股的实时行情列表数据

从 https://quote.eastmoney.com/center/gridlist.html#hs_a_board 页面获取数据
支持分页查询和排序
"""

import json
import random
import re
from typing import Literal

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney._push2_client import fetch_with_retry, warmup_push2


class StockListParams(BaseModel):
    """沪深京A股列表参数模型"""

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量，最大100")
    sort_field: Literal["f2", "f3", "f5", "f6", "f15", "f16"] = Field(
        default="f3",
        description="排序字段，f3=涨跌幅, f2=最新价, f5=成交量, f6=成交额, f15=最高, f16=最低",
    )
    sort_order: int = Field(default=1, ge=0, le=1, description="排序方向，0=升序, 1=降序")


class StockListSpider(BaseWebSpider):
    """
    沪深京A股列表 Spider

    从东方财富网获取沪深京A股的实时行情列表数据
    包括股票代码、名称、最新价、涨跌幅、涨跌额、成交量、成交额等数据
    """

    name = "eastmoney_stock_list"
    description = "获取沪深京A股实时行情列表数据，支持分页和排序"
    version = "2.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockListParams

    # API 配置
    API_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    DEFAULT_UT = "fa5fd1943c7b386f172d6893dbfba10b"
    # 市场筛选：沪深京A股
    # m:0+t:6+f:!2 = 深圳A股(排除ST)
    # m:0+t:80+f:!2 = 深圳创业板(排除ST)
    # m:1+t:2+f:!2 = 上海A股(排除ST)
    # m:1+t:23+f:!2 = 上海科创板(排除ST)
    # m:0+t:81+s:262144+f:!2 = 北交所A股(排除ST)
    MARKET_FILTER = "m:0+t:6+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:81+s:262144+f:!2"
    # 请求字段
    FIELDS = "f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23"

    async def crawl(self, params: StockListParams) -> SpiderResult:
        """
        爬取沪深京A股列表数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # ── 动态提取 ut 令牌：拦截页面加载时自身发起的 push2 API 请求 ──
                captured_ut = {}

                async def capture_ut(route):
                    m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                    if m:
                        captured_ut["token"] = m.group(1)
                    await route.continue_()

                await page.route("**push2.eastmoney.com**", capture_ut)

                await page.goto("https://data.eastmoney.com/")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程
                    pass

                ut = captured_ut.get("token") or self.DEFAULT_UT

                # 暖手 push2 域（建立 quote 域 cookies）
                await warmup_push2(page, fallback_url="https://data.eastmoney.com/")

                # 构建请求参数
                request_params = {
                    "np": "1",
                    "fltt": "1",
                    "invt": "2",
                    "fs": self.MARKET_FILTER,
                    "fields": self.FIELDS,
                    "fid": params.sort_field,
                    "pn": str(params.page),
                    "pz": str(params.page_size),
                    "po": str(params.sort_order),
                    "dect": "1",
                    "ut": ut,
                    "_": str(random.randint(10**12, 10**13 - 1)),
                }

                response_text = await fetch_with_retry(
                    page,
                    self.API_URL,
                    request_params,
                    referer="https://data.eastmoney.com/",
                    response_type="text",
                )

                if response_text is None:
                    return SpiderResult(success=False, message="请求失败")

                # 尝试解析JSONP响应（去除jQuery回调函数）
                json_match = re.search(r"\((.*)\)$", response_text, re.DOTALL)
                if json_match:
                    # JSONP格式
                    data = json.loads(json_match.group(1))
                else:
                    # 尝试直接解析JSON
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

                # 检查是否有数据
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
                            "stocks": [],
                            "page": params.page,
                            "page_size": params.page_size,
                        },
                        message="当前页无数据",
                    )

                # 解析股票列表
                stocks = [self._parse_stock(item) for item in diff_list]

                return SpiderResult(
                    success=True,
                    data={
                        "total": total,
                        "stocks": stocks,
                        "page": params.page,
                        "page_size": params.page_size,
                    },
                    message=f"成功获取第{params.page}页数据，共{len(stocks)}条",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_stock(self, item: dict) -> dict:
        """
        解析单个股票数据

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

        # 字段映射
        # f12: 股票代码
        # f14: 股票名称
        # f2: 最新价
        # f3: 涨跌幅(%)
        # f4: 涨跌额
        # f5: 成交量(手)
        # f6: 成交额(元)
        # f7: 振幅(%)
        # f15: 最高价
        # f16: 最低价
        # f17: 今开价
        # f18: 昨收价
        # f8: 换手率(%)
        # f9: 市盈率(动态)
        # f10: 量比
        # f23: 市净率
        # f152: 市盈率(TTM)

        result = {
            "股票代码": safe_str(item.get("f12")),
            "股票名称": safe_str(item.get("f14")),
            "最新价": round(safe_float(item.get("f2")) / 100, 2),
            "涨跌幅": round(safe_float(item.get("f3")) / 100, 2),
            "涨跌额": round(safe_float(item.get("f4")) / 100, 2),
            "成交量(手)": safe_int(item.get("f5")),
            "成交额(万元)": round(safe_float(item.get("f6")) / 10000, 2),
            "振幅": round(safe_float(item.get("f7")) / 100, 2),
            "最高": round(safe_float(item.get("f15")) / 100, 2),
            "最低": round(safe_float(item.get("f16")) / 100, 2),
            "今开": round(safe_float(item.get("f17")) / 100, 2),
            "昨收": round(safe_float(item.get("f18")) / 100, 2),
            "换手率": round(safe_float(item.get("f8")) / 100, 2),
            "市盈率(动态)": round(safe_float(item.get("f9")), 2),
            "量比": round(safe_float(item.get("f10")), 2),
            "市净率": round(safe_float(item.get("f23")), 2),
            "市盈率(TTM)": round(safe_float(item.get("f152")), 2),
        }

        return result
