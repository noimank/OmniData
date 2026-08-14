"""
东方财富网个股机构买卖统计 Spider
获取单只股票的机构买卖交易历史数据

从 https://data.eastmoney.com/jgzj/ 页面获取个股数据
包括龙虎榜机构交易数据
"""

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class StockOrganizationTradeParams(BaseModel):
    """个股机构买卖统计参数模型"""

    stock_code: str = Field(..., description="股票代码，如 601138、000001")
    limit: int = Field(default=20, ge=1, le=500, description="获取最近多少条数据")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class StockOrganizationTradeSpider(BaseWebSpider):
    """
    个股机构买卖统计 Spider

    从东方财富网获取单只股票的机构买卖交易历史数据
    包括龙虎榜机构交易数据、买入卖出金额、机构数量、上榜原因等
    """

    name = "eastmoney_stock_organization_trade"
    description = "获取单只股票的机构买卖统计数据，包括龙虎榜机构交易明细、买卖金额、上榜原因等"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockOrganizationTradeParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    async def crawl(self, params: StockOrganizationTradeParams) -> SpiderResult:
        """
        爬取个股机构买卖统计数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("eastmoney") as page:
            await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])
            await page.goto("https://data.eastmoney.com/")
            # 构建过滤条件
            filter_str = f'(SECURITY_CODE="{params.stock_code}")'

            # 构建请求参数
            request_params = {
                "callback": "jQuery112302969637654098247_1768630245694",
                "sortColumns": "TRADE_DATE,TRADE_DATE",
                "sortTypes": "-1,-1",
                "pageSize": str(params.limit),
                "pageNumber": "1",
                "reportName": "RPT_ORGANIZATION_TRADE_DETAILSNEW",
                "columns": "ALL",
                "filter": filter_str,
                "source": "WEB",
                "client": "WEB",
            }

            # 发送请求
            response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

            if response.status != 200:
                return SpiderResult(success=False, message=f"请求失败，状态码：{response.status}")

            # 获取响应文本
            response_text = await response.text()

            # 移除 JSONP 回调函数
            # 响应格式可能是：jQuery112302969637654098247_1768630245694({...});
            import re

            json_match = re.search(r"jQuery\d+_\d+\((.*)\);?", response_text)
            if json_match:
                json_str = json_match.group(1)
            elif response_text.startswith("jQuery"):
                # 尝试从第一个 '(' 和最后一个 ')' 之间提取 JSON
                start_idx = response_text.find("(")
                end_idx = response_text.rfind(")")
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx + 1 : end_idx]
                else:
                    json_str = response_text
            else:
                json_str = response_text

            # 解析 JSON
            import json

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                return SpiderResult(success=False, message=f"解析响应数据失败：{str(e)}")

            # 检查返回状态
            # API返回格式: {"version": "...", "result": {"data": [...]}}
            result = data.get("result", {})
            if not result or not result.get("data"):
                return SpiderResult(
                    success=False, message=f"获取数据失败或股票代码不存在：{params.stock_code}"
                )

            # 解析数据
            result_data = self._parse_organization_trade_data(result["data"])

            # 按日期降序排列（最新的在前）
            df = pd.DataFrame(result_data)
            df = df.sort_values("上榜日期", ascending=False).reset_index(drop=True)

            # 获取股票名称
            stock_name = (
                result_data[0].get("股票名称", params.stock_code)
                if result_data
                else params.stock_code
            )

            # 格式化输出
            if params.data_format == "markdown":
                return SpiderResult(
                    success=True,
                    data=df.to_markdown(),
                    message=f"成功获取{stock_name}({params.stock_code})机构买卖统计数据",
                )
            if params.data_format == "string":
                return SpiderResult(
                    success=True,
                    data=df.to_string(),
                    message=f"成功获取{stock_name}({params.stock_code})机构买卖统计数据",
                )

            # 默认返回 dict 格式
            return SpiderResult(
                success=True,
                data=df.to_dict(orient="records"),
                message=f"成功获取{stock_name}({params.stock_code})机构买卖统计数据",
            )

    def _parse_organization_trade_data(self, data: list) -> list[dict]:
        """
        解析机构买卖统计数据

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
        解析单条机构买卖统计数据

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
        trade_date_str = (
            item.get("TRADE_DATE", "")[:10] if item.get("TRADE_DATE") else ""
        )  # 上榜日期
        security_code = safe_str(item.get("SECURITY_CODE"))  # 股票代码
        security_name = safe_str(item.get("SECURITY_NAME_ABBR"))  # 股票名称
        market = safe_str(item.get("MARKET"))  # 市场

        # 价格相关
        close_price = safe_float(item.get("CLOSE_PRICE"))  # 收盘价
        change_rate = safe_float(item.get("CHANGE_RATE"))  # 涨跌幅

        # 机构买卖相关
        buy_count = safe_int(item.get("BUY_COUNT"))  # 买方机构数
        sell_count = safe_int(item.get("SELL_COUNT"))  # 卖方机构数
        buy_times = safe_int(item.get("BUY_TIMES"))  # 买方次数
        sell_times = safe_int(item.get("SELL_TIMES"))  # 卖方次数

        # 金额相关
        buy_amt = safe_float(item.get("BUY_AMT"))  # 机构买入总额
        sell_amt = safe_float(item.get("SELL_AMT"))  # 机构卖出总额
        net_buy_amt = safe_float(item.get("NET_BUY_AMT"))  # 机构买入净额
        accum_amount = safe_float(item.get("ACCUM_AMOUNT"))  # 市场总成交额

        # 比率相关
        ratio = safe_float(item.get("RATIO"))  # 净买额占总成交比
        turnoverrate = safe_float(item.get("TURNOVERRATE"))  # 换手率
        freecap = safe_float(item.get("FREECAP"))  # 流通市值

        # 其他信息
        explanation = safe_str(item.get("EXPLANATION"))  # 上榜原因

        # 上榜后涨跌幅
        d1_close_adjchrate = safe_float(item.get("D1_CLOSE_ADJCHRATE"))  # 上榜后1日
        d2_close_adjchrate = safe_float(item.get("D2_CLOSE_ADJCHRATE"))  # 上榜后2日
        d3_close_adjchrate = safe_float(item.get("D3_CLOSE_ADJCHRATE"))  # 上榜后3日
        d5_close_adjchrate = safe_float(item.get("D5_CLOSE_ADJCHRATE"))  # 上榜后5日
        d10_close_adjchrate = safe_float(item.get("D10_CLOSE_ADJCHRATE"))  # 上榜后10日

        # 构建返回数据
        result = {
            "股票代码": security_code,
            "股票名称": security_name,
            "市场": market,
            "上榜日期": trade_date_str,
            "收盘价": round(close_price, 2),
            "涨跌幅(%)": round(change_rate, 2),
            "买方机构数": buy_count,
            "卖方机构数": sell_count,
            "买方次数": buy_times,
            "卖方次数": sell_times,
            "机构买入总额(万元)": round(buy_amt / 10000, 2),
            "机构卖出总额(万元)": round(sell_amt / 10000, 2),
            "机构买入净额(万元)": round(net_buy_amt / 10000, 2),
            "市场总成交额(万元)": round(accum_amount / 10000, 2),
            "净买额占总成交比(%)": round(ratio, 2),
            "换手率(%)": round(turnoverrate, 2),
            "流通市值(亿元)": round(freecap, 2),
            "上榜原因": explanation,
            "上榜后1日涨跌幅(%)": round(d1_close_adjchrate, 2),
            "上榜后2日涨跌幅(%)": round(d2_close_adjchrate, 2),
            "上榜后3日涨跌幅(%)": round(d3_close_adjchrate, 2),
            "上榜后5日涨跌幅(%)": round(d5_close_adjchrate, 2),
            "上榜后10日涨跌幅(%)": round(d10_close_adjchrate, 2),
        }

        return result
