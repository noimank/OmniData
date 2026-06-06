"""
东方财富网个股融资融券查询 Spider
获取单只股票的融资融券历史数据

从 https://data.eastmoney.com/rzrq/ 页面获取个股数据
支持查询1日、3日、5日、10日等区间统计数据
"""

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class StockMarginTradingParams(BaseModel):
    """个股融资融券参数模型"""

    stock_code: str = Field(..., description="股票代码，如 601138、000001")
    statistics: Literal["1d", "3d", "5d", "10d"] = Field(
        default="1d",
        description="统计周期，可选值：1d(1日数据)、3d(3日合计)、5d(5日合计)、10d(10日合计)",
    )
    limit: int = Field(default=50, ge=1, le=500, description="获取最近多少个交易日的数据")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class StockMarginTradingSpider(BaseWebSpider):
    """
    个股融资融券 Spider

    从东方财富网获取单只股票的融资融券历史数据
    包括融资买入额、融资偿还额、融资净买入额、融券卖出量、融券偿还量、融券净卖出量等数据
    支持多日统计汇总
    """

    name = "eastmoney_stock_margin_trading"
    description = "获取单只股票的融资融券历史数据，支持1日/3日/5日/10日统计周期"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockMarginTradingParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    async def crawl(self, params: StockMarginTradingParams) -> SpiderResult:
        """
        爬取个股融资融券数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])
                await page.goto("https://data.eastmoney.com/")
                # 构建过滤条件
                filter_str = f'(scode="{params.stock_code}")'

                # 构建请求参数
                request_params = {
                    "callback": "datatable1238300",
                    "reportName": "RPTA_WEB_RZRQ_GGMX",
                    "columns": "ALL",
                    "source": "WEB",
                    "sortColumns": "date",
                    "sortTypes": "-1",
                    "pageNumber": "1",
                    "pageSize": str(params.limit),
                    "filter": filter_str,
                    "pageNo": "1",
                }

                # 发送请求
                response = await page.request.get(
                    self.API_URL, params=request_params, timeout=30000
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False, message=f"请求失败，状态码：{response.status}"
                    )

                # 获取响应文本
                response_text = await response.text()

                # 移除 JSONP 回调函数
                # 响应格式可能是：datatable1238300({...});
                import re

                json_match = re.search(r"datatable\d+\((.*)\);?", response_text)
                if json_match:
                    json_str = json_match.group(1)
                elif response_text.startswith("datatable"):
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
                result_data = self._parse_margin_data(result["data"], params.statistics)

                # 按日期降序排列（最新的在前）
                df = pd.DataFrame(result_data)
                df = df.sort_values("交易日期", ascending=False).reset_index(drop=True)

                # 获取股票名称
                stock_name = (
                    result_data[0].get("股票名称", params.stock_code)
                    if result_data
                    else params.stock_code
                )

                # 构建统计周期显示名称
                statistics_name = self._get_statistics_name(params.statistics)

                # 格式化输出
                if params.data_format == "markdown":
                    return SpiderResult(
                        success=True,
                        data=df.to_markdown(),
                        message=f"成功获取{stock_name}({params.stock_code})融资融券{statistics_name}数据",
                    )
                if params.data_format == "string":
                    return SpiderResult(
                        success=True,
                        data=df.to_string(),
                        message=f"成功获取{stock_name}({params.stock_code})融资融券{statistics_name}数据",
                    )

                # 默认返回 dict 格式
                return SpiderResult(
                    success=True,
                    data=df.to_dict(orient="records"),
                    message=f"成功获取{stock_name}({params.stock_code})融资融券{statistics_name}数据",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _get_statistics_name(self, statistics: str) -> str:
        """获取统计周期显示名称"""
        names = {
            "1d": "1日",
            "3d": "3日合计",
            "5d": "5日合计",
            "10d": "10日合计",
        }
        return names.get(statistics, "1日")

    def _parse_margin_data(self, data: list, statistics: str = "1d") -> list[dict]:
        """
        解析融资融券数据

        Args:
            data: API返回的数据数组
            statistics: 统计周期 (1d, 3d, 5d, 10d)

        Returns:
            解析后的数据列表
        """
        result = []

        for item in data:
            parsed_item = self._parse_single_item(item, statistics)
            if parsed_item:
                result.append(parsed_item)

        return result

    def _parse_single_item(self, item: dict, statistics: str = "1d") -> dict | None:
        """
        解析单条融资融券数据

        Args:
            item: API返回的单条数据
            statistics: 统计周期 (1d, 3d, 5d, 10d)

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

        # 根据统计周期选择对应的后缀
        suffix_map = {
            "1d": "",
            "3d": "3D",
            "5d": "5D",
            "10d": "10D",
        }
        suffix = suffix_map.get(statistics, "")

        # 基础信息
        date_str = item.get("DATE", "")[:10] if item.get("DATE") else ""  # 日期
        scode = item.get("SCODE", "")  # 股票代码
        secname = item.get("SECNAME", "")  # 股票名称
        market = item.get("MARKET", "")  # 市场
        trade_market = item.get("TRADE_MARKET", "")  # 交易市场

        # 股价相关
        spj = safe_float(item.get("SPJ"))  # 收盘价
        # 涨跌幅字段根据统计周期变化：1日=ZDF, 3日=RCHANGE3DCP, 5日=RCHANGE5DCP, 10日=RCHANGE10DCP
        zdf_field_map = {
            "1d": "ZDF",
            "3d": "RCHANGE3DCP",
            "5d": "RCHANGE5DCP",
            "10d": "RCHANGE10DCP",
        }
        zdf_field = zdf_field_map.get(statistics, "ZDF")
        zdf = safe_float(item.get(zdf_field))  # 涨跌幅

        # 融资相关
        rz_ye = safe_float(item.get("RZYE"))  # 融资余额(元)
        rq_yl = safe_float(item.get("RQYL"))  # 融券余量(股)
        rzrq_ye = safe_float(item.get("RZRQYE"))  # 融资融券余额(元)
        rq_ye = safe_float(item.get("RQYE"))  # 融券余额(元)

        # 融资相关 - 根据统计周期选择字段
        rz_mre = safe_float(item.get(f"RZMRE{suffix}"))  # 融资买入额(元)
        rz_che = safe_float(item.get(f"RZCHE{suffix}"))  # 融资偿还额(元)
        rz_jme = safe_float(item.get(f"RZJME{suffix}"))  # 融资净买入额(元)

        # 融券相关 - 根据统计周期选择字段
        rq_mcl = safe_float(item.get(f"RQMCL{suffix}" if suffix else "RQMCL"))  # 融券卖出量(股)
        rq_chl = safe_float(item.get(f"RQCHL{suffix}"))  # 融券偿还量(股)
        rq_jmg = safe_float(item.get(f"RQJMG{suffix}"))  # 融券净卖出量(股)

        # 其他字段
        rzrq_yecz = safe_float(item.get("RZRQYECZ"))  # 融资融券余额差额
        sz = safe_float(item.get("SZ"))  # 市值
        rz_yezb = safe_float(item.get("RZYEZB"))  # 融资余额占流通市值比

        # 统计周期显示名称
        statistics_name = self._get_statistics_name(statistics)

        # 构建返回数据
        result = {
            "交易日期": date_str,
            "股票代码": scode,
            "股票名称": secname,
            "市值(亿元)": round(sz / 100000000, 2),
            "市场": market,
            "交易市场": trade_market,
        }

        # 添加股价数据
        result["收盘价"] = round(spj, 2)
        result[f"{statistics_name}涨跌幅(%)"] = round(zdf, 2)

        # 添加融资数据
        result["融资-当日余额(亿元)"] = round(rz_ye / 100000000, 2)
        result[f"融资-{statistics_name}买入额(亿元)"] = round(rz_mre / 100000000, 2)
        result[f"融资-{statistics_name}偿还额(亿元)"] = round(rz_che / 100000000, 2)
        result[f"融资-{statistics_name}净买入(亿元)"] = round(rz_jme / 100000000, 2)
        result["融资-余额占流通市值比(%)"] = round(rz_yezb, 2)

        # 添加融券数据
        result["融券-当日余额(亿元)"] = round(rq_ye / 100000000, 2)
        result["融券-当日余量(万股)"] = round(rq_yl / 10000, 2)
        result[f"融券-{statistics_name}卖出量(万股)"] = round(rq_mcl / 10000, 2)
        result[f"融券-{statistics_name}偿还量(万股)"] = round(rq_chl / 10000, 2)
        result[f"融券-{statistics_name}净卖出(万股)"] = round(rq_jmg / 10000, 2)

        # 添加融资融券余额
        result["融资融券-当日余额(亿元)"] = round(rzrq_ye / 100000000, 2)
        result["融资融券-余额差额(亿元)"] = round(rzrq_yecz / 100000000, 2)

        return result
