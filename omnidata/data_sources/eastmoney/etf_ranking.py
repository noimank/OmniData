"""
东方财富ETF基金最新涨跌排行 Spider
获取沪深两市ETF基金的实时涨跌幅排行榜数据

从 https://quote.eastmoney.com/center/gridlist.html#fund_etf 入口页面加载，
通过浏览器原生请求访问 https://push2.eastmoney.com/api/qt/clist/get，
服务端看到的是带 cookie / referer / sec-ch-ua 等真实浏览器指纹的请求，
反爬风险最低。
"""

import json
import random
import re
from typing import Literal

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney._push2_client import fetch_with_retry


class ETFRankingParams(BaseModel):
    """ETF最新涨跌排行参数模型"""

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量，最大100")
    sort_field: Literal["f2", "f3", "f5", "f6", "f15", "f16"] = Field(
        default="f3",
        description="排序字段，f3=涨跌幅, f2=最新价, f5=成交量, f6=成交额, f15=最高, f16=最低",
    )
    sort_order: Literal["desc", "asc"] = Field(
        default="desc", description="排序方向，desc=降序, asc=升序"
    )


class ETFRankingSpider(BaseWebSpider):
    """
    ETF基金最新涨跌排行 Spider

    从东方财富网获取沪深两市ETF基金的实时行情排行榜数据
    包括基金代码、名称、最新价、涨跌幅、涨跌额、成交量、成交额、最高、最低、今开、昨收、市盈率等数据
    支持分页查询和多种排序方式
    """

    name = "eastmoney_etf_ranking"
    description = "获取沪深两市ETF基金最新涨跌排行数据，支持分页和排序"
    version = "2.1.0"
    author = "noimank"
    platform = "东方财富"

    params_model = ETFRankingParams

    # API 配置
    API_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    DEFAULT_UT = "fa5fd1943c7b386f172d6893dbfba10b"
    # 市场筛选：沪深两市全部ETF
    # b:MK0021 = 上证ETF
    # b:MK0022 = 深证ETF
    # b:MK0023 = 沪深ETF
    # b:MK0024 = 跨境ETF
    # b:MK0827 = 港股ETF
    MARKET_FILTER = "b:MK0021,b:MK0022,b:MK0023,b:MK0024,b:MK0827"
    # 请求字段
    FIELDS = "f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f17,f18,f15,f16"

    # 入口页面：用于动态提取 ut 令牌
    ENTRY_URL = "https://quote.eastmoney.com/center/gridlist.html#fund_etf"

    async def crawl(self, params: ETFRankingParams) -> SpiderResult:
        """
        爬取ETF最新涨跌排行数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
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
                "po": "1" if params.sort_order == "desc" else "0",
                "dect": "1",
                "ut": ut,
                "_": str(random.randint(10**12, 10**13 - 1)),
            }

            response_text = await fetch_with_retry(
                page,
                self.API_URL,
                request_params,
                response_type="text",
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
                        "etfs": [],
                        "page": params.page,
                        "page_size": params.page_size,
                    },
                    message="当前页无数据",
                )

            # 解析ETF列表
            etfs = [self._parse_etf(item) for item in diff_list]

            return SpiderResult(
                success=True,
                data={
                    "total": total,
                    "etfs": etfs,
                    "page": params.page,
                    "page_size": params.page_size,
                },
                message=f"成功获取第{params.page}页ETF排行数据，共{len(etfs)}条",
            )

    def _parse_etf(self, item: dict) -> dict:
        """
        解析单个ETF数据

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
        # f1: 市场代码(0=深圳, 1=上海, 3=?)
        # f12: ETF代码
        # f13: 市场类型(0=深市, 1=沪市)
        # f14: ETF名称
        # f2: 最新价
        # f3: 涨跌幅(%)
        # f4: 涨跌额
        # f5: 成交量(手)
        # f6: 成交额(元)
        # f15: 最高价
        # f16: 最低价
        # f17: 今开价
        # f18: 昨收价
        # f152: 市盈率

        result = {
            "ETF代码": safe_str(item.get("f12")),
            "ETF名称": safe_str(item.get("f14")),
            "市场类型": "沪市ETF" if safe_int(item.get("f13")) == 1 else "深市ETF",
            "最新价": round(safe_float(item.get("f2")) / 1000, 4),
            "涨跌幅(%)": round(safe_float(item.get("f3")) / 100, 2),
            "涨跌额": round(safe_float(item.get("f4")) / 1000, 4),
            "成交量(手)": safe_int(item.get("f5")),
            "成交额(万元)": round(safe_float(item.get("f6")) / 10000, 2),
            "最高": round(safe_float(item.get("f15")) / 1000, 4),
            "最低": round(safe_float(item.get("f16")) / 1000, 4),
            "今开": round(safe_float(item.get("f17")) / 1000, 4),
            "昨收": round(safe_float(item.get("f18")) / 1000, 4),
            # "市盈率": round(safe_float(item.get("f152")), 2),
        }

        return result
