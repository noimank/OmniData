"""
东方财富网市场融资融券查询 Spider
获取沪深北三市融资融券历史数据

从 https://data.eastmoney.com/rzrq/ 页面获取数据
支持查询全部、沪市、深市、京市的融资融券数据
支持1日、3日合计、5日合计、10日合计等区间统计方式
"""

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class MarginTradingParams(BaseModel):
    """市场融资融券参数模型"""

    market: Literal["all", "sh", "sz", "bj"] = Field(
        default="all", description="市场类型，可选值：all(全部)、sh(沪市)、sz(深市)、bj(京市)"
    )
    statistics: Literal["1d", "3d", "5d", "10d"] = Field(
        default="1d",
        description="统计周期，可选值：1d(1日数据)、3d(3日合计)、5d(5日合计)、10d(10日合计)",
    )
    limit: int = Field(default=50, ge=1, le=500, description="获取最近多少个交易日的数据")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class MarginTradingSpider(BaseWebSpider):
    """
    市场融资融券 Spider

    从东方财富网获取沪深北三市融资融券历史数据
    包括融资买入额、融资偿还额、融券卖出量、融券偿还量等数据
    """

    name = "eastmoney_margin_trading"
    description = (
        "获取沪深北三市融资融券历史数据，支持查询全部/沪市/深市/京市，支持1日/3日/5日/10日统计周期"
    )
    version = "1.1.0"
    author = "noimank"
    platform = "东方财富"

    params_model = MarginTradingParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    # 市场配置
    MARKET_CONFIG = {
        "all": {
            "reportName": "RPTA_RZRQ_LSHJ",
            "filter": "",
            "name": "全部",
            "index_name": "沪深300",
        },
        "sh": {
            "reportName": "RPTA_WEB_RZRQ_LSSH",
            "filter": "(SCDM=007)",
            "name": "沪市",
            "index_name": "上证指数",
        },
        "sz": {
            "reportName": "RPTA_WEB_RZRQ_LSSH",
            "filter": "(SCDM=001)",
            "name": "深市",
            "index_name": "深证指数",
        },
        "bj": {
            "reportName": "RPTA_WEB_RZRQ_LSSH",
            "filter": "(SCDM=002)",
            "name": "京市",
            "index_name": "北证50",
        },
    }

    async def crawl(self, params: MarginTradingParams) -> SpiderResult:
        """
        爬取市场融资融券数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                # 获取市场配置
                market_config = self.MARKET_CONFIG[params.market]
                # 构建请求参数
                request_params = {
                    "reportName": market_config["reportName"],
                    "columns": "ALL",
                    "source": "WEB",
                    "sortColumns": "DIM_DATE",
                    "sortTypes": "-1",
                    "pageNumber": "1",
                    "pageSize": str(params.limit),
                    "filter": market_config["filter"],
                }

                # 发送请求
                response = await page.request.get(
                    self.API_URL, params=request_params, timeout=30000
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False, message=f"请求失败，状态码：{response.status}"
                    )

                # 解析响应
                data = await response.json()

                if data is None:
                    return SpiderResult(success=False, message="解析响应数据失败")

                # 检查返回状态
                # API返回格式: {"version": "...", "result": {"data": [...]}}
                result = data.get("result", {})
                if not result or not result.get("data"):
                    return SpiderResult(
                        success=False, message=f"获取数据失败：{data.get('msg', '未知错误')}"
                    )

                # 解析数据，传入统计周期和市场参数
                result_data = self._parse_margin_data(
                    result["data"], params.statistics, params.market
                )

                # 按日期降序排列（最新的在前）
                df = pd.DataFrame(result_data)
                df = df.sort_values("交易日期", ascending=False).reset_index(drop=True)

                # 构建统计周期显示名称
                statistics_name = self._get_statistics_name(params.statistics)

                # 格式化输出
                if params.data_format == "markdown":
                    return SpiderResult(
                        success=True,
                        data=df.to_markdown(),
                        message=f"成功获取{market_config['name']}融资融券{statistics_name}数据",
                    )
                if params.data_format == "string":
                    return SpiderResult(
                        success=True,
                        data=df.to_string(),
                        message=f"成功获取{market_config['name']}融资融券{statistics_name}数据",
                    )

                # 默认返回 dict 格式
                return SpiderResult(
                    success=True,
                    data=df.to_dict(orient="records"),
                    message=f"成功获取{market_config['name']}融资融券{statistics_name}数据",
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

    def _parse_margin_data(
        self, data: list, statistics: str = "1d", market: str = "all"
    ) -> list[dict]:
        """
        解析融资融券数据

        Args:
            data: API返回的数据数组
            statistics: 统计周期 (1d, 3d, 5d, 10d)
            market: 市场类型 (all, sh, sz, bj)

        Returns:
            解析后的数据列表
        """
        result = []

        for item in data:
            # 解析单条数据，传入统计周期和市场参数
            parsed_item = self._parse_single_item(item, statistics, market)
            if parsed_item:
                result.append(parsed_item)

        return result

    def _parse_single_item(
        self, item: dict, statistics: str = "1d", market: str = "all"
    ) -> dict | None:
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

        # 日期
        date_str = item.get("DIM_DATE", "")

        # 指数相关
        index_close = safe_float(item.get("NEW"))  # 指数收盘点位

        # 指数涨跌幅（根据统计周期选择）
        zdf = (
            safe_float(item.get(f"ZDF{suffix}"))
            if statistics != "1d"
            else safe_float(item.get("ZDF"))
        )

        # 融资相关 - 根据统计周期选择字段
        rz_ye = safe_float(item.get("RZYE"))  # 融资余额(元)
        rz_yezb = safe_float(item.get("RZYEZB"))  # 融资余额占流通市值比(%)
        rz_mre = safe_float(item.get(f"RZMRE{suffix}"))  # 融资买入额(元)
        rz_che = safe_float(item.get(f"RZCHE{suffix}"))  # 融资偿还额(元)
        rz_jme = safe_float(item.get(f"RZJME{suffix}"))  # 融资净买入额(元)

        # 融券相关 - 根据统计周期选择字段
        rq_ye = safe_float(item.get("RQYE"))  # 融券余额(元)
        rq_yl = safe_float(item.get("RQYL"))  # 融券余量(股)
        rq_mcl = safe_float(item.get(f"RQMCL{suffix}"))  # 融券卖出量(股)
        rq_chl = safe_float(item.get(f"RQCHL{suffix}"))  # 融券偿还量(股)
        rq_jmg = safe_float(item.get(f"RQJMG{suffix}"))  # 融券净卖出量(股)

        # 融资融券余额（仅1日数据）
        rzrq_ye = safe_float(item.get("RZRQYE")) if statistics == "1d" else 0

        # 获取指数名称
        index_name = self.MARKET_CONFIG[market]["index_name"]

        # 构建返回数据
        result = {
            "交易日期": date_str,
            "指数": index_name,
        }

        # 添加指数数据
        statistics_name = self._get_statistics_name(statistics)
        result[f"当日收盘-{index_name}"] = round(index_close, 2)
        if statistics != "1d":
            result[f"{statistics_name}涨跌幅-{index_name}(%)"] = round(zdf, 2)

        # 添加融资数据
        result["融资-当日余额(亿元)"] = round(rz_ye / 100000000, 2)
        result["融资-当日余额占流通市值比(%)"] = round(rz_yezb, 2)
        result[f"融资-{statistics_name}买入额(亿元)"] = round(rz_mre / 100000000, 2)
        result[f"融资-{statistics_name}偿还额(亿元)"] = round(rz_che / 100000000, 2)
        result[f"融资-{statistics_name}净买入(亿元)"] = round(rz_jme / 100000000, 2)

        # 添加融券数据
        result["融券-当日余额(亿元)"] = round(rq_ye / 100000000, 2)
        result["融券-当日余量(万股)"] = round(rq_yl / 10000, 2)
        result[f"融券-{statistics_name}卖出量(万股)"] = round(rq_mcl / 10000, 2)
        result[f"融券-{statistics_name}偿还量(万股)"] = round(rq_chl / 10000, 2)
        result[f"融券-{statistics_name}净卖出(万股)"] = round(rq_jmg / 10000, 2)

        # 添加融资融券余额（仅1日数据）
        if statistics == "1d":
            result["融资融券-当日余额(亿元)"] = round(rzrq_ye / 100000000, 2)

        return result
