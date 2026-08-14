"""
东方财富网大宗交易市场统计 Spider
获取沪深两市大宗交易市场成交统计数据

从 https://data.eastmoney.com/dzjy/dzjy_sctj.html 页面获取数据
包括每日大宗交易成交总额、溢价成交金额、折价成交金额、上证指数收盘点位
"""

import re
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class BlockTradeMarketStatsParams(BaseModel):
    """大宗交易市场统计参数模型"""

    limit: int = Field(
        default=50, ge=1, le=500, description="获取最近多少个交易日的大宗交易统计数据"
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class BlockTradeMarketStatsSpider(BaseWebSpider):
    """
    大宗交易市场统计 Spider

    从东方财富网获取沪深两市大宗交易市场每日统计数据
    包括成交总额、溢价成交金额、折价成交金额、上证指数收盘点位等
    """

    name = "eastmoney_block_trade_market_stats"
    description = (
        "获取沪深两市大宗交易市场每日统计数据，包括成交总额、溢价/折价成交金额、上证指数等"
    )
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = BlockTradeMarketStatsParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    async def crawl(self, params: BlockTradeMarketStatsParams) -> SpiderResult:
        """
        爬取大宗交易市场统计数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("eastmoney") as page:
            await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])
            await page.goto("https://data.eastmoney.com/dzjy/dzjy_sctj.html")
            # 构建请求参数
            request_params = {
                "reportName": "PRT_BLOCKTRADE_MARKET_STA",
                "columns": "TRADE_DATE,SZ_INDEX,SZ_CHANGE_RATE,BLOCKTRADE_DEAL_AMT,PREMIUM_DEAL_AMT,PREMIUM_RATIO,DISCOUNT_DEAL_AMT,DISCOUNT_RATIO",
                "sortColumns": "TRADE_DATE",
                "sortTypes": "-1",
                "pageNumber": "1",
                "pageSize": str(params.limit),
                "source": "WEB",
                "client": "WEB",
            }

            # 发送请求
            response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

            if response.status != 200:
                return SpiderResult(success=False, message=f"请求失败，状态码：{response.status}")

            # 获取响应文本（JSONP 格式）
            response_text = await response.text()

            # 解析 JSONP 响应：jQuery1123...({...})
            json_match = re.search(r"jQuery\d+\((.*)\);?", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 兜底：尝试从第一个 '(' 和最后一个 ')' 之间提取
                start_idx = response_text.find("(")
                end_idx = response_text.rfind(")")
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx + 1 : end_idx]
                else:
                    json_str = response_text

            import json

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                return SpiderResult(success=False, message=f"解析响应数据失败：{str(e)}")

            # 检查返回状态
            # API返回格式: {"version": "...", "result": {"pages": N, "data": [...]}}
            result = data.get("result", {})
            if not result or not result.get("data"):
                return SpiderResult(
                    success=False, message=f"获取数据失败：{data.get('message', '未知错误')}"
                )

            # 解析数据
            result_data = self._parse_block_trade_data(result["data"])

            if not result_data:
                return SpiderResult(success=False, message="未获取到大宗交易统计数据")

            # 按日期降序排列（最新的在前）
            df = pd.DataFrame(result_data)
            df = df.sort_values("交易日期", ascending=False).reset_index(drop=True)

            # 格式化输出
            if params.data_format == "markdown":
                return SpiderResult(
                    success=True,
                    data=df.to_markdown(),
                    message=f"成功获取大宗交易市场统计 {len(result_data)} 条数据",
                )
            if params.data_format == "string":
                return SpiderResult(
                    success=True,
                    data=df.to_string(),
                    message=f"成功获取大宗交易市场统计 {len(result_data)} 条数据",
                )

            # 默认返回 dict 格式
            return SpiderResult(
                success=True,
                data=df.to_dict(orient="records"),
                message=f"成功获取大宗交易市场统计 {len(result_data)} 条数据",
            )

    def _parse_block_trade_data(self, data: list) -> list[dict]:
        """
        解析大宗交易市场统计数据

        Args:
            data: API返回的数据数组

        Returns:
            解析后的数据列表
        """
        result = []

        for item in data:
            parsed_item = self._parse_single_item(item)
            if parsed_item:
                result.append(parsed_item)

        return result

    def _parse_single_item(self, item: dict) -> dict | None:
        """
        解析单条大宗交易统计数据

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

        # 交易日期（格式：2026-07-31 00:00:00）
        trade_date_raw = item.get("TRADE_DATE", "")
        trade_date = trade_date_raw[:10] if trade_date_raw else ""

        # 上证指数收盘点位
        sz_index = safe_float(item.get("SZ_INDEX"))
        # 上证指数涨跌幅(%)
        sz_change_rate = safe_float(item.get("SZ_CHANGE_RATE"))

        # 大宗交易成交总额（元）
        block_trade_amt = safe_float(item.get("BLOCKTRADE_DEAL_AMT"))
        # 溢价成交金额（元）
        premium_amt = safe_float(item.get("PREMIUM_DEAL_AMT"))
        # 溢价率(%)
        premium_ratio = safe_float(item.get("PREMIUM_RATIO"))
        # 折价成交金额（元）
        discount_amt = safe_float(item.get("DISCOUNT_DEAL_AMT"))
        # 折价率(%)
        discount_ratio = safe_float(item.get("DISCOUNT_RATIO"))

        # 平价成交金额 = 总额 - 溢价 - 折价
        flat_amt = block_trade_amt - premium_amt - discount_amt

        return {
            "交易日期": trade_date,
            "上证指数收盘点位": round(sz_index, 4),
            "上证指数涨跌幅(%)": round(sz_change_rate, 2),
            "大宗成交总额(亿元)": round(block_trade_amt / 100000000, 2),
            "溢价成交金额(亿元)": round(premium_amt / 100000000, 2),
            "溢价率(%)": round(premium_ratio, 2),
            "折价成交金额(亿元)": round(discount_amt / 100000000, 2),
            "折价率(%)": round(discount_ratio, 2),
            "平价成交金额(亿元)": round(flat_amt / 100000000, 2),
        }
