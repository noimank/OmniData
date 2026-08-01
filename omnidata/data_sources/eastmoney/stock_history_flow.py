"""
东方财富网个股历史资金流 Spider
获取个股历史资金流向数据

从东方财富网API直接获取数据
接口地址：https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get
"""

import json
import random
import re
from typing import Literal

import pandas as pd
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney._push2_client import fetch_with_retry, warmup_push2


class StockHistoryFlowParams(BaseModel):
    """个股历史资金流参数模型"""

    stock_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="股票或ETF代码，如 000001（平安银行）、516920（芯片ETF）",
    )
    limit: int = Field(default=30, ge=0, le=220, description="获取最近多少个交易日的资金流数据")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class StockHistoryFlowSpider(BaseWebSpider):
    """
    个股历史资金流 Spider

    从东方财富网API直接获取个股历史资金流向数据
    返回 DataFrame 格式的表格数据
    """

    name = "eastmoney_stock_history_flow"
    description = "获取个股/ETF历史资金流向数据"
    version = "2.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockHistoryFlowParams

    # API 配置
    API_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    DEFAULT_UT = "b2884a393a59ad64002292a3e90d46a5"
    FIELDS1 = "f1,f2,f3,f7"
    FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"

    async def crawl(self, params: StockHistoryFlowParams) -> SpiderResult:
        """
        爬取个股历史资金流数据

        数据来源：东方财富网API
        通过直接请求API获取个股历史资金流向数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            # 判断股票所属市场
            # 上海市场：600xxx, 601xxx, 603xxx, 605xxx, 688xxx
            # 深圳市场：000xxx, 001xxx, 002xxx, 003xxx, 300xxx, 301xxx
            first_char = params.stock_code[0]

            if first_char == "6" or first_char == "5":
                market_code = "1"  # 上海市场
            else:
                market_code = "0"  # 深圳市场

            secid = f"{market_code}.{params.stock_code}"

            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # ── 动态提取 ut 令牌：拦截页面加载时自身发起的 push2his API 请求 ──
                captured_ut = {}

                async def capture_ut(route):
                    m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                    if m:
                        captured_ut["token"] = m.group(1)
                    await route.continue_()

                await page.route("**push2his.eastmoney.com**", capture_ut)

                await page.goto("https://data.eastmoney.com/")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程
                    pass

                ut = captured_ut.get("token") or self.DEFAULT_UT

                # 构建请求参数
                request_params = {
                    "lmt": params.limit if params.limit > 0 else 0,
                    "klt": "101",  # 日K线
                    "fields1": self.FIELDS1,
                    "fields2": self.FIELDS2,
                    "ut": ut,
                    "secid": secid,
                    "_": str(random.randint(10**12, 10**13 - 1)),
                }

                # 暖手 quote 域，建立 push2 接口所需 cookies
                await warmup_push2(page, fallback_url="https://data.eastmoney.com/")

                text = await fetch_with_retry(
                    page,
                    self.API_URL,
                    request_params,
                    referer="https://data.eastmoney.com/",
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
                        success=False, message=f"获取数据失败，请检查股票代码是否存在！"
                    )

                # 获取数据内容
                klines = data.get("data", {}).get("klines", [])

                if not klines:
                    return SpiderResult(
                        success=False, message=f"未找到股票代码 {params.stock_code} 的资金流数据"
                    )

                # 解析 K线数据（逗号分隔的字符串）
                klines = [line.split(",") for line in klines]

                # 构建数据列表
                data_list = []

                for kline in klines:
                    if len(kline) >= 13:
                        date_str = kline[0]  # 格式: "2024-10-30"

                        # 解析数值
                        close_price = self._safe_float(kline[11])  # 收盘价
                        change_pct = self._safe_float(kline[12])  # 涨跌幅

                        # 主力净流入
                        main_net_amount = self._safe_float(kline[1])  # 净额（元）
                        main_net_ratio = self._safe_float(kline[6])  # 净占比（百分比）

                        # 超大单净流入
                        super_large_net_amount = self._safe_float(kline[5])  # 净额（元）
                        super_large_net_ratio = self._safe_float(kline[10])  # 净占比（百分比）

                        # 大单净流入
                        large_net_amount = self._safe_float(kline[4])  # 净额（元）
                        large_net_ratio = self._safe_float(kline[9])  # 净占比（百分比）

                        # 中单净流入
                        medium_net_amount = self._safe_float(kline[3])  # 净额（元）
                        medium_net_ratio = self._safe_float(kline[8])  # 净占比（百分比）

                        # 小单净流入
                        small_net_amount = self._safe_float(kline[2])  # 净额（元）
                        small_net_ratio = self._safe_float(kline[7])  # 净占比（百分比）

                        data_list.append(
                            {
                                "日期": date_str,
                                "收盘价": close_price,
                                "涨跌幅(%)": change_pct,
                                "主力净流入净额(亿元)": round(
                                    main_net_amount / 100000000, 2
                                ),  # 转换为亿元
                                "主力净流入净占比(%)": main_net_ratio,
                                "超大单净流入净额(亿元)": round(
                                    super_large_net_amount / 100000000, 2
                                ),  # 转换为亿元
                                "超大单净流入净占比(%)": super_large_net_ratio,
                                "大单净流入净额(亿元)": round(
                                    large_net_amount / 100000000, 2
                                ),  # 转换为亿元
                                "大单净流入净占比(%)": large_net_ratio,
                                "中单净流入净额(亿元)": round(
                                    medium_net_amount / 100000000, 2
                                ),  # 转换为亿元
                                "中单净流入净占比(%)": medium_net_ratio,
                                "小单净流入净额(亿元)": round(
                                    small_net_amount / 100000000, 2
                                ),  # 转换为亿元
                                "小单净流入净占比(%)": small_net_ratio,
                            }
                        )

                # 转换为 DataFrame
                df = pd.DataFrame(data_list)

                # 按日期降序排列（最新的在前）
                df = df.sort_values("日期", ascending=False).reset_index(drop=True)

                # 如果API已经限制了条数，就不需要再次截取
                # 但为了确保，还是按照用户要求截取
                if params.limit > 0 and len(df) > params.limit:
                    df = df.head(params.limit)

                result_data = df.to_dict(orient="records")
                if params.data_format == "markdown":
                    result_data = df.to_markdown()
                if params.data_format == "string":
                    result_data = df.to_string()

                return SpiderResult(
                    success=True,
                    data=result_data,
                    message=f"成功获取股票代码 {params.stock_code} 的历史资金流数据共{len(df)}条",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

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
