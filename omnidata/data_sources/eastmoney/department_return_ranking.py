"""
东方财富网营业部收益率排行 Spider
获取营业部收益率排行榜数据

从东方财富网获取营业部收益率排行数据
包括营业部名称、上榜次数、收益率、交易金额等
"""

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class DepartmentReturnRankingParams(BaseModel):
    """营业部收益率排行参数模型"""

    statistics_cycle: Literal["01", "02", "03", "04"] = Field(
        default="01",
        description="统计周期：01=近1月，02=近3月，03=近6月，04=近1年"
    )
    limit: int = Field(default=50, ge=1, description="获取数据条数")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, string, markdown"
    )


class DepartmentReturnRankingSpider(BaseWebSpider):
    """
    营业部收益率排行 Spider

    从东方财富网获取营业部收益率排行榜数据
    包括营业部名称、上榜次数、收益率、交易金额等
    """

    name = "eastmoney_department_return_ranking"
    description = "获取营业部收益率排行榜数据，包括营业部上榜次数、收益率、交易金额等"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = DepartmentReturnRankingParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    async def crawl(self, params: DepartmentReturnRankingParams) -> SpiderResult:
        """
        爬取营业部收益率排行数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                # 构建过滤条件
                filter_str = f'(STATISTICSCYCLE="{params.statistics_cycle}")'

                # 分页请求获取数据
                all_data = []
                page_number = 1
                page_size = 50  # 每页固定50条
                total = 0
                pages = 0

                while len(all_data) < params.limit:
                    # 构建请求参数
                    request_params = {
                        "sortColumns": "TOTAL_BUYER_SALESTIMES_1DAY,OPERATEDEPT_CODE",
                        "sortTypes": "-1,1",
                        "pageSize": str(page_size),
                        "pageNumber": str(page_number),
                        "reportName": "RPT_RATEDEPT_RETURNT_RANKING",
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
                    import re
                    json_match = re.search(r'jQuery\d+_\d+\((.*)\);?', response_text)
                    if json_match:
                        json_str = json_match.group(1)
                    elif response_text.startswith("jQuery"):
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

                    # 检查返回状态
                    result = data.get("result", {})
                    if not result:
                        if page_number == 1:
                            return SpiderResult(
                                success=False,
                                message=f"获取数据失败，请检查统计周期是否正确"
                            )
                        break

                    data_list = result.get("data", [])
                    total = result.get("count", 0)
                    pages = result.get("pages", 0)

                    if not data_list:
                        break

                    all_data.extend(data_list)

                    # 如果已获取足够数据或已到最后一页，停止请求
                    if len(all_data) >= params.limit or page_number >= pages:
                        break

                    page_number += 1

                # 如果没有数据
                if not all_data:
                    return SpiderResult(
                        success=True,
                        data=[],
                        message=f"统计周期 {params.statistics_cycle} 无营业部收益率排行数据"
                    )

                # 截取到指定数量
                all_data = all_data[:params.limit]

                # 解析数据
                result_data = self._parse_ranking_data(all_data)

                # 按上榜次数降序排列
                df = pd.DataFrame(result_data)

                # 统计周期映射
                cycle_map = {"01": "近1月", "03": "近3月", "06": "近6月", "12": "近1年"}

                # 构建统计信息
                stats_info = {
                    "returned_count": len(result_data),
                    "total_count": total,
                    "statistics_cycle": cycle_map.get(params.statistics_cycle, params.statistics_cycle),
                }

                # 格式化输出
                if params.data_format == "markdown":
                    return SpiderResult(
                        success=True,
                        data={
                            "stats": stats_info,
                            "records": df.to_markdown(),
                        },
                        message=f"成功获取营业部收益率排行数据（共 {len(result_data)} 条，总计 {total} 条）"
                    )
                if params.data_format == "string":
                    return SpiderResult(
                        success=True,
                        data={
                            "stats": stats_info,
                            "records": df.to_string(),
                        },
                        message=f"成功获取营业部收益率排行数据（共 {len(result_data)} 条，总计 {total} 条）"
                    )

                # 默认返回 dict 格式
                return SpiderResult(
                    success=True,
                    data={
                        "stats": stats_info,
                        "records": df.to_dict(orient="records"),
                    },
                    message=f"成功获取营业部收益率排行数据（共 {len(result_data)} 条，总计 {total} 条）"
                )

        except Exception as e:
            return SpiderResult(
                success=False,
                message=f"爬取失败：{str(e)}"
            )

    def _parse_ranking_data(self, data: list) -> list[dict]:
        """
        解析营业部收益率排行数据

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
        解析单条营业部收益率排行数据

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

        # 营业部信息
        operate_dept_name = safe_str(item.get("OPERATEDEPT_NAME"))  # 营业部名称
        operate_dept_code = safe_str(item.get("OPERATEDEPT_CODE"))  # 营业部代码
        operate_dept_code_old = safe_str(item.get("OPERATEDEPT_CODE_OLD"))  # 旧营业部代码

        # 后1日数据
        average_increase_1day = safe_float(item.get("AVERAGE_INCREASE_1DAY"))  # 后1日平均涨幅
        rise_probability_1day = safe_float(item.get("RISE_PROBABILITY_1DAY"))  # 后1日上涨概率
        total_buyer_saletimes_1day = safe_int(item.get("TOTAL_BUYER_SALESTIMES_1DAY"))  # 后1日上榜次数

        # 后2日数据
        average_increase_2day = safe_float(item.get("AVERAGE_INCREASE_2DAY"))  # 后2日平均涨幅
        rise_probability_2day = safe_float(item.get("RISE_PROBABILITY_2DAY"))  # 后2日上涨概率
        total_buyer_saletimes_2day = safe_int(item.get("TOTAL_BUYER_SALESTIMES_2DAY"))  # 后2日上榜次数

        # 后3日数据
        average_increase_3day = safe_float(item.get("AVERAGE_INCREASE_3DAY"))  # 后3日平均涨幅
        rise_probability_3day = safe_float(item.get("RISE_PROBABILITY_3DAY"))  # 后3日上涨概率
        total_buyer_saletimes_3day = safe_int(item.get("TOTAL_BUYER_SALESTIMES_3DAY"))  # 后3日上榜次数

        # 后5日数据
        average_increase_5day = safe_float(item.get("AVERAGE_INCREASE_5DAY"))  # 后5日平均涨幅
        rise_probability_5day = safe_float(item.get("RISE_PROBABILITY_5DAY"))  # 后5日上涨概率
        total_buyer_saletimes_5day = safe_int(item.get("TOTAL_BUYER_SALESTIMES_5DAY"))  # 后5日上榜次数

        # 后10日数据
        average_increase_10day = safe_float(item.get("AVERAGE_INCREASE_10DAY"))  # 后10日平均涨幅
        rise_probability_10day = safe_float(item.get("RISE_PROBABILITY_10DAY"))  # 后10日上涨概率
        total_buyer_saletimes_10day = safe_int(item.get("TOTAL_BUYER_SALESTIMES_10DAY"))  # 后10日上榜次数

        # 构建返回数据
        result = {
            "营业部名称": operate_dept_name,
            "营业部代码": operate_dept_code,
            # "营业部旧代码": operate_dept_code_old,
            "后1日上榜次数": total_buyer_saletimes_1day,
            "后1日平均涨幅(%)": round(average_increase_1day, 2),
            "后1日上涨概率(%)": round(rise_probability_1day, 2),
            "后2日上榜次数": total_buyer_saletimes_2day,
            "后2日平均涨幅(%)": round(average_increase_2day, 2),
            "后2日上涨概率(%)": round(rise_probability_2day, 2),
            "后3日上榜次数": total_buyer_saletimes_3day,
            "后3日平均涨幅(%)": round(average_increase_3day, 2),
            "后3日上涨概率(%)": round(rise_probability_3day, 2),
            "后5日上榜次数": total_buyer_saletimes_5day,
            "后5日平均涨幅(%)": round(average_increase_5day, 2),
            "后5日上涨概率(%)": round(rise_probability_5day, 2),
            "后10日上榜次数": total_buyer_saletimes_10day,
            "后10日平均涨幅(%)": round(average_increase_10day, 2),
            "后10日上涨概率(%)": round(rise_probability_10day, 2),
        }

        return result
