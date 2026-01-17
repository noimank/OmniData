"""
东方财富网个股龙虎榜 Spider
获取A股个股的历史龙虎榜上榜数据

从 https://datacenter-web.eastmoney.com/api/data/v1/get 接口获取数据
支持查询个股的龙虎榜历史记录，包括上榜原因、涨跌幅、买卖金额等
"""

import random
import re
import time
from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class StockBillboardParams(BaseModel):
    """个股龙虎榜参数模型"""

    stock_code: str = Field(
        ...,
        min_length=6, max_length=6,
        description="股票代码，6位数字，例如：000001(平安银行)、600000(浦发银行)"
    )
    start_date: str = Field(
        default="20200101",
        pattern=r"^\d{8}$",
        description="开始日期，格式：yyyyMMdd，例如：20200101，默认20200101"
    )
    end_date: str = Field(
        default="20500101",
        pattern=r"^\d{8}$",
        description="结束日期，格式：yyyyMMdd，例如：20251231，默认20500101"
    )

    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, string, markdown"
    )


class StockBillboardSpider(BaseWebSpider):
    """
    个股龙虎榜 Spider

    从东方财富网获取A股个股的历史龙虎榜数据
    包括交易日期、上榜原因、收盘价、涨跌幅、净买卖金额、营业部净买入等
    以及上榜后1/2/3/5/10/20/30日的涨跌幅数据
    """

    name = "eastmoney_stock_billboard"
    description = "获取A股个股历史龙虎榜上榜数据，包括上榜原因、涨跌幅、买卖金额、营业部净买入以及上榜后多日涨跌幅等完整数据，支持日期范围查询"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockBillboardParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    @staticmethod
    def _generate_jsonp_callback() -> str:
        """
        生成随机 jQuery JSONP 回调函数名
        模拟真实浏览器请求格式：jQuery + 18位随机数 + _ + 13位时间戳

        Returns:
            随机回调函数名，例如：jQuery112304786753408034462_1768642295465
        """
        random_part = ''.join([str(random.randint(0, 9)) for _ in range(18)])
        timestamp = str(int(time.time() * 1000))
        return f"jQuery{random_part}_{timestamp}"

    def _format_date(self, date_str: str) -> str:
        """
        将yyyyMMdd格式转换为yyyy-MM-dd格式

        Args:
            date_str: 日期字符串，格式：yyyyMMdd

        Returns:
            转换后的日期字符串，格式：yyyy-MM-dd
        """
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except Exception:
            return date_str

    async def crawl(self, params: StockBillboardParams) -> SpiderResult:
        """
        爬取个股龙虎榜数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        context = await self.get_context_simple("eastmoney")
        page = await context.new_page()
        try:
            await self.apply_anti_detection_scripts(page, "advanced")

            # 格式化日期
            start_date_formatted = self._format_date(params.start_date)
            end_date_formatted = self._format_date(params.end_date)

            # 构建 filter 参数
            # 格式：(SECURITY_CODE="601138")(TRADE_DATE>='2025-01-17')
            filter_str = f'(SECURITY_CODE="{params.stock_code}")(TRADE_DATE>=\'{start_date_formatted}\')(TRADE_DATE<=\'{end_date_formatted}\')'

            # 构建请求参数
            request_params = {
                "callback": self._generate_jsonp_callback(),
                "sortColumns": "TRADE_DATE,TRADE_DATE",
                "sortTypes": "-1,-1",  # 降序
                # "pageSize": str(params.page_size), 不需要
                "pageNumber": "1",
                "reportName": "RPT_BILLBOARD_PERFORMANCEHIS",
                "columns": "ALL",
                "filter": filter_str,
                "source": "WEB",
                "client": "WEB",
            }


            # 发送请求
            response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

            if response.status != 200:
                return SpiderResult(
                    success=False,
                    message=f"请求失败，状态码：{response.status}"
                )

            # 获取响应文本
            response_text = await response.text()

            # 移除 JSONP 回调函数
            # 响应格式：jQuery{random}_{timestamp}({...});
            # 例如：jQuery112304786753408034462_1768642295467({...});
            json_match = re.search(r'jQuery[\d_]+\((.*)\);?', response_text)
            if json_match:
                json_str = json_match.group(1)
            elif response_text.startswith("jQuery"):
                # 尝试从第一个 '(' 和最后一个 ')' 之间提取 JSON
                start_idx = response_text.find('(')
                end_idx = response_text.rfind(')')
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx + 1:end_idx]
                else:
                    json_str = response_text
            else:
                json_str = response_text

            # 解析 JSON
            import json
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                return SpiderResult(
                    success=False,
                    message=f"解析响应数据失败：{str(e)}"
                )

            # 检查返回数据
            result = data.get("result", {})
            if not result or not result.get("data"):
                return SpiderResult(
                    success=False,
                    message=f"未找到股票代码 {params.stock_code} 的龙虎榜数据，该股票可能未上过龙虎榜"
                )

            # 解析数据
            billboard_data = result.get("data", [])
            parsed_data = self._parse_billboard_data(billboard_data)

            # 转换为 DataFrame 并按日期升序排列（最早的在前）
            df = pd.DataFrame(parsed_data)
            if not df.empty:
                df = df.sort_values("交易日期", ascending=True).reset_index(drop=True)

            # 获取股票名称
            stock_name = parsed_data[0].get("股票名称", params.stock_code) if parsed_data else params.stock_code

            # 格式化输出
            if params.data_format == "markdown":
                return SpiderResult(
                    success=True,
                    data=df.to_markdown() if not df.empty else [],
                    message=f"成功获取 {stock_name}({params.stock_code}) 龙虎榜数据，共{len(parsed_data)}条"
                )
            if params.data_format == "string":
                return SpiderResult(
                    success=True,
                    data=df.to_string() if not df.empty else [],
                    message=f"成功获取 {stock_name}({params.stock_code}) 龙虎榜数据，共{len(parsed_data)}条"
                )

            # 默认返回 dict 格式
            return SpiderResult(
                success=True,
                data=df.to_dict(orient="records") if not df.empty else [],
                message=f"成功获取 {stock_name}({params.stock_code}) 龙虎榜数据，共{len(parsed_data)}条"
            )

        except Exception as e:
            return SpiderResult(
                success=False,
                message=f"爬取失败：{str(e)}"
            )
        finally:
            await page.close()
            await context.close()

    def _parse_billboard_data(self, billboard_data: list) -> list[dict]:
        """
        解析龙虎榜数据

        Args:
            billboard_data: API返回的龙虎榜数据列表

        Returns:
            解析后的数据列表
        """
        result = []

        def safe_float(value) -> float:
            """安全地将值转换为 float"""
            if value is None or value == "" or value == "-":
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0

        def safe_str(value) -> str:
            """安全地将值转换为 str"""
            if value is None:
                return ""
            return str(value)

        for item in billboard_data:
            # 解析交易日期
            trade_date = item.get("TRADE_DATE", "")
            if trade_date:
                # 格式：2025-09-12 00:00:00 -> 2025-09-12
                trade_date = trade_date.split(" ")[0]

            parsed_item = {
                "股票代码": safe_str(item.get("SECURITY_CODE", "")),
                "股票名称": safe_str(item.get("SECURITY_NAME_ABBR", "")),
                "交易日期": trade_date,
                "收盘价": round(safe_float(item.get("CLOSE_PRICE")), 2),
                "涨跌幅(%)": round(safe_float(item.get("CHANGE_RATE")), 2),
                "上榜原因": safe_str(item.get("EXPLAIN", "")),
                "上榜营业部买入合计(万元)": round(safe_float(item.get("NET_BUY_AMT")) / 10000, 2),
                "上榜营业部卖出合计(万元)": round(safe_float(item.get("NET_SELL_AMT")) / 10000, 2),
                "上榜营业部买卖净额(万元)": round(safe_float(item.get("NET_OPERATEDEPT_AMT")) / 10000, 2),
                "上榜后1日涨跌幅(%)": round(safe_float(item.get("D1_CLOSE_ADJCHRATE")), 2),
                "上榜后2日涨跌幅(%)": round(safe_float(item.get("D2_CLOSE_ADJCHRATE")), 2),
                "上榜后3日涨跌幅(%)": round(safe_float(item.get("D3_CLOSE_ADJCHRATE")), 2),
                "上榜后5日涨跌幅(%)": round(safe_float(item.get("D5_CLOSE_ADJCHRATE")), 2),
                "上榜后10日涨跌幅(%)": round(safe_float(item.get("D10_CLOSE_ADJCHRATE")), 2),
                "上榜后20日涨跌幅(%)": round(safe_float(item.get("D20_CLOSE_ADJCHRATE")), 2),
                "上榜后30日涨跌幅(%)": round(safe_float(item.get("D30_CLOSE_ADJCHRATE")), 2),
            }

            result.append(parsed_item)

        return result
