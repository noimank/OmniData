"""
东方财富网大盘资金流 Spider
获取沪深两市大盘资金流向历史数据

从 https://data.eastmoney.com/zjlx/dpzjlx.html 页面获取数据
提取 #table_ls 表格内容并转换为 DataFrame 格式
"""

import json
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class MarketFlowParams(BaseModel):
    """大盘资金流参数模型"""

    limit: int = Field(default=1, ge=0, le=120, description="获取最近多少个交易日的资金流数据")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, string, markdown"
    )


class MarketFlowSpider(BaseWebSpider):
    """
    大盘资金流 Spider

    从 https://data.eastmoney.com/zjlx/dpzjlx.html 获取沪深两市大盘资金流向数据
    返回 DataFrame 格式的表格数据，与页面 #table_ls 表格一致
    """

    name = "eastmoney_market_flow"
    description = "获取沪深两市大盘资金流向历史数据"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = MarketFlowParams

    async def crawl(self, params: MarketFlowParams) -> SpiderResult:
        """
        爬取沪深两市大盘资金流历史数据

        数据来源：东方财富网大盘资金流向页面
        通过访问页面并拦截 API 请求获取数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                # 用于存储拦截到的数据
                captured_data = {}

                # 拦截 API 请求
                async def handle_route(route):
                    """拦截并处理 API 请求"""
                    try:
                        url = route.request.url
                        if "push2his.eastmoney.com/api/qt/stock/fflow/daykline/get" in url:
                            # 获取响应数据
                            response = await route.fetch()
                            body = await response.body()
                            try:
                                captured_data["api_response"] = self._parse_jsonp(body)
                            except Exception:
                                captured_data["api_response"] = None
                            # 继续请求，不中断页面正常加载
                            await route.continue_()
                            # await route.abort()
                        else:
                            await route.continue_()
                    except Exception:
                        # 出错时继续请求，避免影响页面加载
                        await route.continue_()

                # 设置路由拦截
                await page.route("**/*", handle_route)

                # 访问页面，触发 API 请求
                await page.goto("https://data.eastmoney.com/zjlx/dpzjlx.html")

                # 等待 API 请求被拦截（最多等待 10 秒）
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=3000)
                except Exception:
                    pass

                # 检查是否成功获取数据
                if "api_response" not in captured_data:
                    return SpiderResult(
                        success=False,
                        message="获取数据失败：未拦截到 API 响应"
                    )

                data = captured_data["api_response"]

                # 解析返回数据
                if data.get("rc") != 0 or not data.get("data"):
                    return SpiderResult(
                        success=False,
                        message="获取数据失败"
                    )

                # 获取数据内容
                klines = data["data"].get("klines", [])
                klines = [line.split(",") for line in klines]

                # 构建数据列表
                data_list = []

                for kline in klines:
                    if len(kline) >= 15:
                        date_str = kline[0]  # 格式: "2024-10-30"

                        # 解析数值
                        sh_close = self._safe_float(kline[11])
                        sh_change = self._safe_float(kline[12])
                        sz_close = self._safe_float(kline[13])
                        sz_change = self._safe_float(kline[14])

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

                        data_list.append({
                            "日期": date_str,
                            "上证收盘价": sh_close,
                            "上证涨跌幅(%)": sh_change,
                            "深证收盘价": sz_close,
                            "深证涨跌幅(%)": sz_change,
                            "主力净流入净额(亿元)": round(main_net_amount / 100000000, 2),  # 转换为亿元
                            "主力净流入净占比(%)": main_net_ratio,
                            "超大单净流入净额(亿元)": round(super_large_net_amount / 100000000, 2),  # 转换为亿元
                            "超大单净流入净占比(%)": super_large_net_ratio,
                            "大单净流入净额(亿元)": round(large_net_amount / 100000000, 2),  # 转换为亿元
                            "大单净流入净占比(%)": large_net_ratio,
                            "中单净流入净额(亿元)": round(medium_net_amount / 100000000, 2),  # 转换为亿元
                            "中单净流入净占比(%)": medium_net_ratio,
                            "小单净流入净额(亿元)": round(small_net_amount / 100000000, 2),  # 转换为亿元
                            "小单净流入净占比(%)": small_net_ratio,
                        })

                # 转换为 DataFrame
                df = pd.DataFrame(data_list)

                # 按日期降序排列（最新的在前）
                df = df.sort_values("日期", ascending=False).reset_index(drop=True)
                # 截取数据
                df = df.head(params.limit)

                result_data = df.to_dict(orient="records")
                if params.data_format == "markdown":
                    result_data = df.to_markdown()
                if params.data_format == "string":
                    result_data = df.to_string()

                return SpiderResult(
                    success=True,
                    data=result_data
                )
        except Exception as e:
            return SpiderResult(success=False, message=f"获取数据失败: {str(e)}")

    @staticmethod
    def _parse_jsonp(body: bytes) -> dict | None:
        """
        解析 JSONP 格式的响应数据

        Args:
            body: 响应体字节数据

        Returns:
            解析后的字典，解析失败返回 None
        """
        try:
            text = body.decode("utf-8")
            # 提取括号内的 JSON 数据
            # 格式：jQuery1234567890({...}) 或 callback({...})
            start_idx = text.find("(")
            end_idx = text.rfind(")")
            if start_idx > 0 and end_idx > start_idx:
                json_text = text[start_idx + 1:end_idx]
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
