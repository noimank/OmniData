"""
新浪财经个股当日实时分时 Spider
获取个股当日（含盘中）的实时分钟线数据（分钟级 开/高/低/收/成交量/成交额）

数据来源：新浪财经 quotes.sina.cn 实时分钟 K 线接口
    https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_x=/CN_MarketDataService.getKLineData?symbol={symbol}&scale=1&ma=no&datalen=241
scale=1 即 1 分钟线，datalen=241 覆盖一个完整交易日（沪深 A 股 241 个交易分钟）。
接口返回最近 N 根分钟线（跨交易日边界）：盘中返回当日已产生分钟线 + 上一交易日溢出，
收盘后返回当日完整 241 根。爬虫按返回数据的最大日期过滤出当日分时，故盘中即可拿到
当日实时数据（与历史月度文件的区别：历史文件需当日收盘后归档才可得）。

接口返回纯 JSONP（非压缩混淆），直接经浏览器上下文（page.request）拉取即可，无需
浏览器内解码。返回字段：day(分钟时间戳)/open/high/low/close/volume/amount，无均价。
免登录、免 API Key，接口门槛仅为新浪财经域 Referer 头。成交量单位与新浪分时口径一致
（沪深个股为股，指数/基金为手）。
"""

import asyncio
import json
import logging
import re
from typing import Any, Literal

import pandas as pd
from playwright.async_api import Page
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult

logger = logging.getLogger(__name__)


class StockMinlineRealtimeParams(BaseModel):
    """个股当日实时分时参数模型"""

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
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        description="返回分时条数上限，取当日最近 N 条；默认不填返回全部",
    )


class StockMinlineRealtimeSpider(BaseWebSpider):
    """
    新浪财经个股当日实时分时 Spider

    获取个股当日的实时分钟线数据（分钟级 开盘/最高/最低/收盘/成交量/成交额），盘中即
    可获取当日已产生分时，收盘后返回当日完整 241 个交易分钟。数据来自新浪 quotes.sina.cn
    实时分钟 K 线接口（scale=1），按返回数据最大日期过滤出当日分时。免登录、免 API Key。
    """

    name = "sina_stock_minline_realtime"
    description = (
        "获取个股/ETF当日实时分时数据（分钟级开盘/最高/最低/收盘/成交量/成交额），盘中即可获取，"
    )
    version = "1.0.0"
    author = "noimank"
    platform = "新浪财经"

    params_model = StockMinlineRealtimeParams

    # API 配置 - 新浪实时分钟 K 线接口（jsonp 包装，返回纯 JSON 无需解码）
    API_BASE = "https://quotes.sina.cn/cn/api/jsonp_v2.php"
    # 单交易日沪深 A 股交易分钟数（09:30–11:30 + 13:01–15:00 = 241）
    DATA_LEN = 241
    # 暖手访问的新浪财经入口页：同源环境 + 累积 sina 域 cookie
    ENTRY_URL = "https://finance.sina.com.cn/"
    # 实时行情接口（仅用于取证券名称）
    QUOTE_API = "https://hq.sinajs.cn/list"
    REFERER = "https://finance.sina.com.cn/"
    # 入口页加载超时（毫秒）
    PAGE_TIMEOUT_MS = 15000
    # 名称请求超时（毫秒）
    REQUEST_TIMEOUT_MS = 8000
    # 请求失败时的最大重试次数（指数退避 1s/2s）
    MAX_RETRIES = 3

    async def crawl(self, params: StockMinlineRealtimeParams) -> SpiderResult:
        """
        爬取个股当日实时分时数据

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

        url = (
            f"{self.API_BASE}/var%20_minline_1=/CN_MarketDataService.getKLineData"
            f"?symbol={symbol}&scale=1&ma=no&datalen={self.DATA_LEN}"
        )

        async with self.new_page("sina") as page:
            await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

            # 先访问新浪财经首页：拟人化访问链路（真实用户先浏览首页再拉行情）并累积
            # sina 域 cookie 到上下文。加载失败不影响后续请求
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

            text = await self._fetch_text(page, url)
            if text is None:
                return SpiderResult(success=False, message="请求失败，请稍后重试")

            records = self._parse_records(text)
            if not records:
                return SpiderResult(success=False, message="未获取到分时数据，请稍后重试")

            # 接口返回最近 N 根分钟线（跨交易日边界），按最大日期过滤出当日分时
            trade_date = max(r["day"][:10] for r in records)
            day_records = [r for r in records if r["day"].startswith(trade_date)]
            if not day_records:
                return SpiderResult(success=False, message="当日无分时数据")

            # 指定 limit 时只保留当日最近 N 条（保持时间升序）
            if params.limit is not None:
                day_records = day_records[-params.limit :]

            minutes = [self._to_minute(rec) for rec in day_records]

            code = symbol[2:]
            display_name = name or symbol
            summary = {
                "证券代码": code,
                "证券名称": display_name,
                "日期": trade_date,
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
                    f"成功获取 {display_name}({code}) {trade_date} 分时数据共 {len(minutes)} 条"
                ),
            )

    async def _fetch_text(self, page: Page, url: str) -> str | None:
        """
        经浏览器上下文请求实时分钟 K 线接口并返回响应文本，含指数退避重试

        Args:
            page: Playwright Page 对象，使用其 request 走真实浏览器请求
            url: 目标接口 URL

        Returns:
            响应文本；最终失败返回 None
        """
        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await page.request.get(
                    url,
                    headers={"Referer": self.REFERER},
                    timeout=self.REQUEST_TIMEOUT_MS,
                )
                if response.status == 200:
                    return await response.text()
            except Exception as e:
                last_error = e
            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)
        if last_error is not None:
            logger.warning(
                "sina minline realtime fetch failed after %d retries (%s): %s",
                self.MAX_RETRIES,
                url,
                last_error,
            )
        return None

    @staticmethod
    def _parse_records(text: str) -> list[dict]:
        """
        解析 jsonp 响应为分钟线记录列表

        响应形如：/*<script>...*/\\nvar _minline_1=([{...},{...}]);
        直接截取首个 '[' 至末个 ']' 之间的 JSON 数组，过滤出含 day 字段的字典。

        Args:
            text: jsonp 响应文本

        Returns:
            分钟线记录列表；解析失败返回空列表
        """
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end < start:
            return []
        try:
            data = json.loads(text[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        return [r for r in data if isinstance(r, dict) and "day" in r]

    @staticmethod
    def _to_minute(rec: dict) -> dict:
        """
        将单条分钟线记录转为结构化字典（时间取 HH:MM，数值字段安全转换）

        Args:
            rec: 含 day/open/high/low/close/volume/amount 的原始记录

        Returns:
            结构化分钟字典
        """

        def to_float(value: Any) -> float | None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def to_int(value: Any) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        return {
            "时间": rec["day"][11:16],
            "开盘": to_float(rec.get("open")),
            "最高": to_float(rec.get("high")),
            "最低": to_float(rec.get("low")),
            "收盘": to_float(rec.get("close")),
            "成交量": to_int(rec.get("volume")),
            "成交额": to_float(rec.get("amount")),
        }

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
