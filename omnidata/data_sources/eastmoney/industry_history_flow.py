"""
东方财富网行业历史资金流 Spider
获取指定行业板块的历史资金流向数据

数据说明：
- 主力资金 = 超大单 + 大单
- 超大单：单笔成交额 >= 50万元
- 大单：20万元 <= 单笔成交额 < 50万元
- 中单：5万元 <= 单笔成交额 < 20万元
- 小单：单笔成交额 < 5万元

API 来源：https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get
"""

import re
from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class IndustryHistoryFlowParams(BaseModel):
    """行业历史资金流参数模型"""

    sector_code: str = Field(
        ...,
        description="行业板块代码，如：BK0737（软件开发）、BK0420（航空机场）",
        examples=["BK0737", "BK0420"],
    )
    period: Literal["day", "week", "month"] = Field(
        default="day",
        description="K线周期：day=日线, week=周线, month=月线",
    )
    limit: int = Field(
        default=0,
        ge=0,
        description="限制返回数据条数，0表示全部数据",
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回格式：json, dict, markdown, string"
    )


class IndustryHistoryFlowSpider(BaseWebSpider):
    """行业历史资金流 Spider"""

    name = "eastmoney_industry_history_flow"
    description = "获取指定行业板块的历史资金流向数据（日线/周线/月线）"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"
    params_model = IndustryHistoryFlowParams

    PAGE_URL = "https://data.eastmoney.com/bkzj/BK0737.html"
    API_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"

    # K线周期映射
    PERIOD_MAP = {"day": "101", "week": "102", "month": "103"}
    PERIOD_DESC = {"day": "日线", "week": "周线", "month": "月线"}

    async def crawl(self, params: IndustryHistoryFlowParams) -> SpiderResult:
        try:
            # 构建完整的 secid（市场代码90 + 板块代码）
            secid = f"90.{params.sector_code}"

            # 转换周期参数为API所需的klt值
            klt = self.PERIOD_MAP[params.period]

            async with self.new_page("eastmoney") as page:
                await self.apply_anti_detection_scripts(page, "advanced")
                await page.goto(self.PAGE_URL)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)

                # 请求历史资金流数据
                response = await page.request.get(
                    self.API_URL,
                    params={
                        "lmt": str(params.limit),
                        "klt": klt,
                        "fields1": "f1,f2,f3,f7",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
                        "ut": "b2884a393a59ad64002292a3e90d46a5",
                        "secid": secid,
                    },
                    timeout=30000,
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False, message=f"API请求失败，状态码：{response.status}"
                    )

                data = await response.json()

                if data.get("rc") != 0:
                    return SpiderResult(
                        success=False, message=f"API返回错误：{data.get('message', '未知错误')}"
                    )

                # 解析数据
                result_data = data.get("data", {})
                klines = result_data.get("klines", [])

                if not klines:
                    return SpiderResult(success=True, data=[], message="未获取到历史数据")

                # 解析K线数据
                data_list = [self._parse_kline(kline) for kline in klines]
                df = pd.DataFrame(data_list)

                # 添加板块信息
                metadata = {
                    "板块代码": result_data.get("code", ""),
                    "板块名称": result_data.get("name", ""),
                    "市场代码": result_data.get("market", ""),
                    "K线周期": self.PERIOD_DESC[params.period],
                    "数据条数": len(data_list),
                }

                result_output = df.to_dict(orient="records")
                if params.data_format == "markdown":
                    result_output = df.to_markdown()
                elif params.data_format == "string":
                    result_output = df.to_string()

                return SpiderResult(
                    success=True,
                    data={"metadata": metadata, "klines": result_output},
                    message=f"成功获取 {len(data_list)} 条历史数据",
                )
        except Exception as e:
            return SpiderResult(success=False, message=f"数据爬取失败：{str(e)}")

    def _parse_kline(self, kline: str) -> dict:
        """解析K线数据字符串

        K线数据格式（逗号分隔，共15个字段）：
        0: 日期
        1: 主力净流入
        2: 小单净流入
        3: 中单净流入
        4: 大单净流入
        5: 超大单净流入
        6: 主力净占比
        7: 小单净占比
        8: 中单净占比
        9: 大单净占比
        10: 超大单净占比
        11: 收盘价
        12: 涨跌幅
        13-14: 预留字段
        """
        fields = kline.split(",")

        def safe_float(v):
            try:
                return float(v) if v not in (None, "") else 0.0
            except (ValueError, TypeError):
                return 0.0

        return {
            "日期": fields[0] if len(fields) > 0 else "",
            "主力净流入(亿)": (
                round(safe_float(fields[1]) / 100000000, 2) if len(fields) > 1 else 0.0
            ),
            "主力净占比(%)": safe_float(fields[6]) if len(fields) > 6 else 0.0,
            "超大单净流入(亿)": (
                round(safe_float(fields[5]) / 100000000, 2) if len(fields) > 5 else 0.0
            ),
            "超大单净占比(%)": safe_float(fields[10]) if len(fields) > 10 else 0.0,
            "大单净流入(亿)": (
                round(safe_float(fields[4]) / 100000000, 2) if len(fields) > 4 else 0.0
            ),
            "大单净占比(%)": safe_float(fields[9]) if len(fields) > 9 else 0.0,
            "中单净流入(亿)": (
                round(safe_float(fields[3]) / 100000000, 2) if len(fields) > 3 else 0.0
            ),
            "中单净占比(%)": safe_float(fields[8]) if len(fields) > 8 else 0.0,
            "小单净流入(亿)": (
                round(safe_float(fields[2]) / 100000000, 2) if len(fields) > 2 else 0.0
            ),
            "小单净占比(%)": safe_float(fields[7]) if len(fields) > 7 else 0.0,
            "收盘价": safe_float(fields[11]) if len(fields) > 11 else 0.0,
            "涨跌幅(%)": safe_float(fields[12]) if len(fields) > 12 else 0.0,
        }
