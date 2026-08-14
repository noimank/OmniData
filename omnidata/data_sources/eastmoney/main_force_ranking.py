"""
东方财富主力净流入排名 Spider
获取沪深A股主力资金净流入排行榜数据

通过统一客户端 _push2_client 在东财页面内 fetch push2 JSONP 接口获取数据。
"""

import json
import random
import re
from datetime import datetime
from typing import Literal

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney._push2_client import fetch_with_retry


class MainForceRankingParams(BaseModel):
    """主力净流入排行参数模型"""

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=50, ge=1, le=100, description="每页数量，最大100")
    sort_field: Literal["f184", "f62", "f3", "f109"] = Field(
        default="f184",
        description=(
            "排序字段，"
            "f184=主力净占比, "
            "f62=主力净流入(元), "
            "f3=涨跌幅, "
            "f109=主力净流入占比"
        ),
    )
    sort_order: Literal["desc", "asc"] = Field(
        default="desc", description="排序方向，desc=降序, asc=升序"
    )
    market: Literal["all", "sh", "sz", "kcb", "cyb", "sh_b", "sz_b"] = Field(
        default="all",
        description=(
            "市场范围："
            "all=沪深A股, sh=沪市A股, sz=深市A股, "
            "kcb=科创板, cyb=创业板, sh_b=沪市B股, sz_b=深市B股"
        ),
    )


class MainForceRankingSpider(BaseWebSpider):
    """
    主力净流入排名 Spider

    从东方财富网获取沪深A股的主力资金净流入排行榜数据
    包括代码、名称、最新价、涨跌幅、所属行业、主力净流入、主力净占比、
    今日/5日/10日 排名与涨跌、所属板块等数据
    支持分页查询、多种排序方式以及市场筛选
    """

    name = "eastmoney_main_force_ranking"
    description = "获取沪深两市主力资金净流入排行数据，支持分页、排序（主力净占比/主力净流入/涨跌幅等）和市场筛选"
    version = "2.1.0"
    author = "noimank"
    platform = "东方财富"

    params_model = MainForceRankingParams

    # API 配置
    API_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    DEFAULT_UT = "8dec03ba335b81bf4ebdf7b29ec27d15"

    # 市场筛选：沪深京A股
    # m:0 = 深市, m:1 = 沪市
    # t:2 = 沪深A股, t:6 = B股, t:13 = 创业板, t:23 = 科创板, t:80 = 北证A股
    # f:!2 = 排除ST（?东方财富接口中 f:!2 含义需结合 fs 实际效果使用）
    MARKET_FILTERS = {
        "all": "m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2",
        "sh": "m:1+t:2+f:!2,m:1+t:23+f:!2",
        "sz": "m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2",
        "kcb": "m:1+t:23+f:!2",
        "cyb": "m:0+t:13+f:!2",
        "sh_b": "m:1+t:5+f:!2",
        "sz_b": "m:0+t:5+f:!2",
    }

    # 请求字段
    FIELDS = (
        "f1,f2,f3,f12,f13,f14,f62,f100,f109,f124,f160,f164,f165,f166,f168,f170,f172,"
        "f174,f175,f176,f178,f180,f182,f184,f225,f263,f264,f265"
    )

    # 入口页面：用于动态提取 ut 令牌
    ENTRY_URL = "https://data.eastmoney.com/zjlx/list.html"

    async def crawl(self, params: MainForceRankingParams) -> SpiderResult:
        """
        爬取主力净流入排行数据

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

            market_filter = self.MARKET_FILTERS.get(params.market, self.MARKET_FILTERS["all"])

            # 构建请求参数
            request_params = {
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fs": market_filter,
                "fields": self.FIELDS,
                "fid": params.sort_field,
                "pn": str(params.page),
                "pz": str(params.page_size),
                "po": "1" if params.sort_order == "desc" else "0",
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
                        "stocks": [],
                        "page": params.page,
                        "page_size": params.page_size,
                        "market": params.market,
                        "sort_field": params.sort_field,
                        "sort_order": params.sort_order,
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
                    "market": params.market,
                    "sort_field": params.sort_field,
                    "sort_order": params.sort_order,
                },
                message=f"成功获取第{params.page}页主力净流入排行，共{len(stocks)}条",
            )

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

        # 字段映射：
        # f1: 市场类型(2=沪深京A股)
        # f2: 最新价
        # f3: 今日涨跌幅(%)
        # f12: 股票代码
        # f13: 市场ID(0=深市, 1=沪市)
        # f14: 股票名称
        # f62: 主力净流入(元)
        # f100: 所属行业
        # f109: 5日涨跌幅(%)
        # f124: 时间戳
        # f160: 10日涨跌幅(%)
        # f164: 5日主力净流入(元)
        # f165: 5日主力净流入占比(%)
        # f166: 5日超大单净流入(元)
        # f168: 5日大单净流入(元)
        # f170: 5日中单净流入(元)
        # f172: 5日小单净流入(元)
        # f174: 10日主力净流入(元)
        # f175: 10日主力净流入占比(%)
        # f176: 10日超大单净流入(元)
        # f178: 10日大单净流入(元)
        # f180: 10日中单净流入(元)
        # f182: 10日小单净流入(元)
        # f184: 主力净占比(%) (今日, 也是默认排序字段)
        # f225: 今日排名
        # f263: 5日排名
        # f264: 10日排名
        # f265: 板块代码

        update_ts = safe_int(item.get("f124"))
        update_time = (
            datetime.fromtimestamp(update_ts).strftime("%Y-%m-%d %H:%M:%S") if update_ts else ""
        )

        result = {
            "代码": safe_str(item.get("f12")),
            "名称": safe_str(item.get("f14")),
            "市场": "沪市" if safe_int(item.get("f13")) == 1 else "深市",
            "最新价": round(safe_float(item.get("f2")), 2),
            "今日主力净占比(%)": round(safe_float(item.get("f184")), 2),
            "今日涨跌幅(%)": round(safe_float(item.get("f3")), 2),
            "今日排名": safe_int(item.get("f225")),
            "5日主力净占比(%)": round(safe_float(item.get("f165")), 2),
            "5日涨跌幅(%)": round(safe_float(item.get("f109")), 2),
            "5日排名": safe_int(item.get("f263")),
            "10日主力净占比(%)": round(safe_float(item.get("f175")), 2),
            "10日涨跌幅(%)": round(safe_float(item.get("f160")), 2),
            "10日排名": safe_int(item.get("f264")),
            "所属行业": safe_str(item.get("f100")),
            "板块代码": safe_str(item.get("f265")),
            "主力净流入(万元)": round(safe_float(item.get("f62")) / 10000, 2),
            "5日主力净流入(万元)": round(safe_float(item.get("f164")) / 10000, 2),
            "5日超大单净流入(万元)": round(safe_float(item.get("f166")) / 10000, 2),
            "5日大单净流入(万元)": round(safe_float(item.get("f168")) / 10000, 2),
            "5日中单净流入(万元)": round(safe_float(item.get("f170")) / 10000, 2),
            "5日小单净流入(万元)": round(safe_float(item.get("f172")) / 10000, 2),
            "10日主力净流入(万元)": round(safe_float(item.get("f174")) / 10000, 2),
            "10日超大单净流入(万元)": round(safe_float(item.get("f176")) / 10000, 2),
            "10日大单净流入(万元)": round(safe_float(item.get("f178")) / 10000, 2),
            "10日中单净流入(万元)": round(safe_float(item.get("f180")) / 10000, 2),
            "10日小单净流入(万元)": round(safe_float(item.get("f182")) / 10000, 2),
            "更新时间": update_time,
        }

        return result
