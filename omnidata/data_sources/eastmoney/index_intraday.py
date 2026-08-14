"""
东方财富网指数分时 Spider
获取指数分时数据（分钟级别）

从东方财富网API直接获取数据
接口地址：https://push2.eastmoney.com/api/qt/stock/trends2/get

字段顺序：时间,开盘,收盘,最高,最低,成交量,成交额,最新价
"""

import json
import random
import re
from typing import Literal

import pandas as pd
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney._push2_client import fetch_with_retry


class IndexIntradayParams(BaseModel):
    """指数分时参数模型"""

    index_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="指数代码，如 000001（上证指数）、399001（深证成指）、399006（创业板指）、000300（沪深300）、000688（科创50）",
    )
    limit: int = Field(default=0, ge=0, le=2000, description="获取最近多少条分时数据，0表示全部")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class IndexIntradaySpider(BaseWebSpider):
    """
    指数分时 Spider

    从东方财富网API直接获取指数分时数据（分钟级别）
    返回 DataFrame 格式的表格数据
    """

    name = "eastmoney_index_intraday"
    description = "获取指数最新分时数据（分钟级别），包括开高低收、成交量、成交额"
    version = "2.1.0"
    author = "noimank"
    platform = "东方财富"

    params_model = IndexIntradayParams

    # API 配置
    API_URL = "https://push2.eastmoney.com/api/qt/stock/trends2/get"
    DEFAULT_UT = "fa5fd1943c7b386f172d6893dbfba10b"
    FIELDS1 = "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
    FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58"

    # 指数所属市场映射
    # 上海市场指数：000xxx（上证综指系列）、999xxx
    # 深圳市场指数：399xxx（深证成指系列）
    SHANGHAI_PREFIXES = ("000", "999")

    async def crawl(self, params: IndexIntradayParams) -> SpiderResult:
        """
        爬取指数分时数据

        数据来源：东方财富网API
        通过直接请求API获取指数分时数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        # 判断指数所属市场
        market_code = self._market_of(params.index_code)
        secid = f"{market_code}.{params.index_code}"

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

            # 构建请求参数
            request_params = {
                "secid": secid,
                "fields1": self.FIELDS1,
                "fields2": self.FIELDS2,
                "iscr": "0",
                "ndays": "1",
                "ut": ut,
                "_": str(random.randint(10**12, 10**13 - 1)),
            }

            text = await fetch_with_retry(
                page,
                self.API_URL,
                request_params,
                response_type="text",
            )

            if text is None:
                return SpiderResult(success=False, message="请求失败")

            # 解析响应（可能是JSONP格式）
            body = text.encode("utf-8")
            data = self._parse_response(body)

            if data is None:
                return SpiderResult(success=False, message="解析响应数据失败")

            # 检查返回状态
            if data.get("rc") != 0:
                return SpiderResult(
                    success=False, message=f"获取数据失败，请检查指数代码是否存在！"
                )

            payload = data.get("data") or {}
            index_name = payload.get("name") or params.index_code
            trends = payload.get("trends", [])

            if not trends:
                return SpiderResult(
                    success=False,
                    message=f"未找到指数代码 {params.index_code} 的分时数据",
                )

            # 解析分时数据
            # 字段顺序：时间,开盘,收盘,最高,最低,成交量,成交额,最新价
            data_list = []
            for row in trends:
                cols = row.split(",")
                if len(cols) < 8:
                    continue
                data_list.append(
                    {
                        "时间": cols[0],
                        "开盘": self._safe_float(cols[1]),
                        "收盘": self._safe_float(cols[2]),
                        "最高": self._safe_float(cols[3]),
                        "最低": self._safe_float(cols[4]),
                        "成交量": self._safe_int(cols[5]),
                        # "成交额": self._safe_float(cols[6]),
                        "成交额(亿元)": round(self._safe_float(cols[6]) / 1e8, 4),
                        "最新价": self._safe_float(cols[7]),
                    }
                )

            df = pd.DataFrame(data_list)

            # 按时间升序排列（最早的在前，便于阅读）
            df = df.sort_values("时间", ascending=True).reset_index(drop=True)

            # 如果用户指定了限制条数且大于0
            if params.limit > 0 and len(df) > params.limit:
                df = df.tail(params.limit).reset_index(drop=True)

            result_data = df.to_dict(orient="records")
            if params.data_format == "markdown":
                result_data = df.to_markdown()
            elif params.data_format == "string":
                result_data = df.to_string()

            return SpiderResult(
                success=True,
                data=result_data,
                message=(f"成功获取指数 {index_name}({params.index_code}) 分时数据共{len(df)}条"),
            )

    def _market_of(self, index_code: str) -> str:
        """根据指数代码判断所属市场（secid 第一段：1=沪，0=深）"""
        if index_code[:3] in self.SHANGHAI_PREFIXES:
            return "1"
        return "0"

    def _parse_response(self, body: bytes) -> dict | None:
        """
        解析响应数据（支持JSON和JSONP格式）

        Args:
            body: 响应体字节数据

        Returns:
            解析后的字典，解析失败返回 None
        """
        try:
            text = body.decode("utf-8")

            # 尝试直接解析JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

            # 如果是JSONP格式，提取JSON数据
            # 格式：jQuery1234567890({...}) 或 callback({...})
            start_idx = text.find("(")
            end_idx = text.rfind(")")
            if start_idx > 0 and end_idx > start_idx:
                json_text = text[start_idx + 1 : end_idx]
                return json.loads(json_text)

            return None
        except Exception:
            return None

    @staticmethod
    def _safe_float(value: str | int | float | None) -> float:
        """安全地将值转换为 float"""
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _safe_int(value: str | int | float | None) -> int:
        """安全地将值转换为 int"""
        if value is None or value == "":
            return 0
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0
