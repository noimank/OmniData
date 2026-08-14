"""
东方财富外汇市场行情 Spider
获取外汇市场中各外汇品种的实时行情列表数据

从 https://quote.eastmoney.com/center/gridlist.html#forex_all 入口页面加载，
通过浏览器原生请求访问 https://push2.eastmoney.com/weblogin/api/qt/clist/get，
服务端看到的是带 cookie / referer / sec-ch-ua 等真实浏览器指纹的请求，
反爬风险最低。

外汇行情字段说明：
- f1:  市场类型（4=外汇中间价/交叉盘）
- f2:  最新价（原始值除以 10000 还原）
- f3:  涨跌幅（万分位）
- f4:  涨跌额（原始值除以 10000 还原）
- f12: 货币对代码（如 EURHUF、GBPCNYC）
- f13: 市场ID（119=主要外汇、120=人民币中间价、133=离岸人民币）
- f14: 货币对中文名称
- f15: 最高价（原始值除以 10000 还原）
- f16: 最低价（原始值除以 10000 还原）
- f17: 今开价（原始值除以 10000 还原）
- f18: 昨收价（原始值除以 10000 还原）
- f152: 显示精度位数（仅展示用，实际还原统一除以 10000）

所有价格字段在 API 端统一乘以 10000 存储以避免浮点误差，
还原真实汇率时统一除以 10000。例如：
- JPYCNYC: f2=42203 → 4.2203
- EURHUF:  f2=3647455 → 364.7455
- JPYCHF:  f2=5126 → 0.5126
"""

import json
import random
import re
from typing import Literal

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney._push2_client import fetch_with_retry


class ForexMarketParams(BaseModel):
    """外汇市场行情参数模型"""

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量，最大100")
    sort_field: Literal["f2", "f3", "f4", "f12"] = Field(
        default="f3",
        description="排序字段，f3=涨跌幅, f2=最新价, f4=涨跌额, f12=货币对代码",
    )
    sort_order: Literal["desc", "asc"] = Field(
        default="desc", description="排序方向，desc=降序, asc=升序"
    )
    market: Literal["all", "119", "120", "133"] = Field(
        default="all",
        description=(
            "外汇市场筛选："
            "all=全部外汇行情, "
            "119=外汇行情(主要货币对), "
            "120=外汇行情(中间价), "
            "133=外汇行情(交叉盘)"
        ),
    )


class ForexMarketSpider(BaseWebSpider):
    """
    外汇市场行情 Spider

    从东方财富网获取外汇市场中各货币对的实时行情数据
    包括货币对代码、中文名称、最新价、涨跌幅、涨跌额、最高、最低、今开、昨收等数据
    支持分页查询、排序和市场筛选
    """

    name = "eastmoney_forex_market"
    description = "获取外汇市场各货币对实时行情数据，支持分页、排序和市场筛选"
    version = "1.1.0"
    author = "noimank"
    platform = "东方财富"

    params_model = ForexMarketParams

    # API 配置（外汇接口使用 weblogin 子域路径）
    API_URL = "https://push2.eastmoney.com/weblogin/api/qt/clist/get"
    DEFAULT_UT = "fa5fd1943c7b386f172d6893dbfba10b"

    # 市场筛选（m:119=主要外汇、m:120=人民币中间价、m:133=外汇交叉盘）
    MARKET_FILTER = "m:119,m:120,m:133"
    # 请求字段
    FIELDS = "f12,f13,f14,f1,f2,f4,f3,f152,f17,f18,f15,f16"

    # 入口页面：用于动态提取 ut 令牌
    ENTRY_URL = "https://quote.eastmoney.com/center/gridlist.html#forex_all"

    async def crawl(self, params: ForexMarketParams) -> SpiderResult:
        """
        爬取外汇市场行情数据

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

            # 构建 fs 参数
            fs = self._build_fs(params.market)

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
                        "forex": [],
                        "page": params.page,
                        "page_size": params.page_size,
                        "market": params.market,
                        "sort_field": params.sort_field,
                        "sort_order": params.sort_order,
                    },
                    message="当前页无数据",
                )

            # 解析外汇列表
            forex_list = [self._parse_forex(item) for item in diff_list]

            return SpiderResult(
                success=True,
                data={
                    "total": total,
                    "forex": forex_list,
                    "page": params.page,
                    "page_size": params.page_size,
                    "market": params.market,
                    "sort_field": params.sort_field,
                    "sort_order": params.sort_order,
                },
                message=f"成功获取第{params.page}页外汇行情，共{len(forex_list)}条",
            )

    def _build_fs(self, market: str) -> str:
        """
        构建 fs 参数（外汇市场筛选）

        Args:
            market: 市场标识（all/119/120/133）

        Returns:
            fs 参数字符串
        """
        if market == "all":
            return self.MARKET_FILTER
        return f"m:{market}"

    def _parse_forex(self, item: dict) -> dict:
        """
        解析单个外汇行情数据

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

        # 东方财富外汇接口所有价格字段统一乘以 10000 存储，
        # 需要除以 10000 还原真实汇率（f152 表示显示精度，但存储统一为 10000 倍）。
        # 例：JPYCNYC f2=42203 → 4.2203、EURHUF f2=3647455 → 364.7455
        divisor = 10000

        market_id = safe_int(item.get("f13"))
        market_label = {
            119: "主要外汇",
            120: "人民币中间价",
            133: "外汇交叉盘",
        }.get(market_id, f"其他({market_id})")

        result = {
            "货币对代码": safe_str(item.get("f12")),
            "货币对名称": safe_str(item.get("f14")),
            "市场": market_label,
            "最新价": round(safe_float(item.get("f2")) / divisor, 4),
            "涨跌幅(%)": round(safe_float(item.get("f3")) / 100, 2),
            "涨跌额": round(safe_float(item.get("f4")) / divisor, 4),
            "最高": round(safe_float(item.get("f15")) / divisor, 4),
            "最低": round(safe_float(item.get("f16")) / divisor, 4),
            "今开": round(safe_float(item.get("f17")) / divisor, 4),
            "昨收": round(safe_float(item.get("f18")) / divisor, 4),
        }

        return result
