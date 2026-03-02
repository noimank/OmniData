"""
东方财富网活跃营业部 Spider
获取指定日期范围的龙虎榜活跃营业部数据

从 https://data.eastmoney.com/lhb/ 页面获取营业部数据
包括营业部名称、买入卖出金额、净买入额、上榜次数、交易股票等
"""

from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class ActiveDepartmentParams(BaseModel):
    """活跃营业部参数模型"""

    start_date: str = Field(
        default="", description="开始日期，格式：YYYY-MM-DD，如 2026-01-14，默认为当天"
    )
    end_date: str = Field(
        default="", description="结束日期，格式：YYYY-MM-DD，如 2026-01-16，默认为当天"
    )
    limit: int = Field(default=60, ge=1, le=1000, description="获取数据条数，最多1000条")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class ActiveDepartmentSpider(BaseWebSpider):
    """
    活跃营业部 Spider

    从东方财富网获取指定日期范围的龙虎榜活跃营业部数据
    包括营业部名称、买入卖出金额、净买入额、上榜次数、交易股票等
    """

    name = "eastmoney_active_department"
    description = "获取指定日期范围的龙虎榜活跃营业部数据，包括营业部买卖金额、净买入额、上榜次数等"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = ActiveDepartmentParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    async def crawl(self, params: ActiveDepartmentParams) -> SpiderResult:
        """
        爬取活跃营业部数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """

        try:
            async with self.new_page("eastmoney") as page:
                # 处理默认日期（当天）
                today = datetime.now().strftime("%Y-%m-%d")

                # 如果两个日期都为空，默认为当天
                # 如果只指定了一个日期，另一个也使用相同的日期
                if not params.start_date and not params.end_date:
                    start_date = today
                    end_date = today
                elif params.start_date and not params.end_date:
                    start_date = params.start_date
                    end_date = params.start_date
                elif not params.start_date and params.end_date:
                    start_date = params.end_date
                    end_date = params.end_date
                else:
                    start_date = params.start_date
                    end_date = params.end_date

                # 验证日期格式
                try:
                    datetime.strptime(start_date, "%Y-%m-%d")
                    datetime.strptime(end_date, "%Y-%m-%d")
                except ValueError:
                    return SpiderResult(
                        success=False, message="日期格式错误，请使用 YYYY-MM-DD 格式，如 2026-01-14"
                    )

                # 构建过滤条件
                filter_str = f"(ONLIST_DATE>='{start_date}')(ONLIST_DATE<='{end_date}')"

                # 分页请求获取数据
                all_data = []
                page_number = 1
                page_size = 50  # 每页固定50条
                total = 0
                pages = 0

                while len(all_data) < params.limit:
                    # 构建请求参数
                    request_params = {
                        "sortColumns": "TOTAL_NETAMT,ONLIST_DATE,OPERATEDEPT_CODE",
                        "sortTypes": "-1,-1,1",
                        "pageSize": str(page_size),
                        "pageNumber": str(page_number),
                        "reportName": "RPT_OPERATEDEPT_ACTIVE",
                        "columns": "ALL",
                        "filter": filter_str,
                        "source": "WEB",
                        "client": "WEB",
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
                    import re

                    json_match = re.search(r"jQuery\d+_\d+\((.*)\);?", response_text)
                    if json_match:
                        json_str = json_match.group(1)
                    elif response_text.startswith("jQuery"):
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
                    result = data.get("result", {})
                    if not result:
                        if page_number == 1:
                            return SpiderResult(
                                success=False, message=f"获取数据失败，请检查日期范围是否正确"
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
                        message=f"指定日期范围 {start_date} 至 {end_date} 无活跃营业部数据",
                    )

                # 截取到指定数量
                all_data = all_data[: params.limit]

                # 解析数据
                result_data = self._parse_department_data(all_data)

                # 按净买入额降序排列
                df = pd.DataFrame(result_data)
                # df = df.sort_values("总买卖净额(万元)", ascending=False).reset_index(drop=True)

                # 构建统计信息
                stats_info = {
                    "returned_count": len(result_data),
                    "total_count": total,
                    "date_range": f"{start_date} 至 {end_date}",
                }

                # 格式化输出
                if params.data_format == "markdown":
                    return SpiderResult(
                        success=True,
                        data={
                            "stats": stats_info,
                            "records": df.to_markdown(),
                        },
                        message=f"成功获取活跃营业部数据（共 {len(result_data)} 条，总计 {total} 条）",
                    )
                if params.data_format == "string":
                    return SpiderResult(
                        success=True,
                        data={
                            "stats": stats_info,
                            "records": df.to_string(),
                        },
                        message=f"成功获取活跃营业部数据（共 {len(result_data)} 条，总计 {total} 条）",
                    )

                # 默认返回 dict 格式
                return SpiderResult(
                    success=True,
                    data={
                        "stats": stats_info,
                        "records": df.to_dict(orient="records"),
                    },
                    message=f"成功获取活跃营业部数据（共 {len(result_data)} 条，总计 {total} 条）",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_department_data(self, data: list) -> list[dict]:
        """
        解析活跃营业部数据

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
        解析单条活跃营业部数据

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
        org_name_abbr = safe_str(item.get("ORG_NAME_ABBR"))  # 机构简称

        # 日期信息
        onlist_date_str = (
            item.get("ONLIST_DATE", "")[:10] if item.get("ONLIST_DATE") else ""
        )  # 上榜日期

        # 上榜次数
        buyer_appear_num = safe_int(item.get("BUYER_APPEAR_NUM"))  # 买方上榜次数
        seller_appear_num = safe_int(item.get("SELLER_APPEAR_NUM"))  # 卖方上榜次数

        # 金额相关（单位：元）
        total_buy_amt = safe_float(item.get("TOTAL_BUYAMT"))  # 总买入金额
        total_sell_amt = safe_float(item.get("TOTAL_SELLAMT"))  # 总卖出金额
        total_net_amt = safe_float(item.get("TOTAL_NETAMT"))  # 总净买入金额

        # 交易股票
        buy_stock = safe_str(item.get("BUY_STOCK"))  # 买入股票代码
        security_name_abbr = safe_str(item.get("SECURITY_NAME_ABBR"))  # 股票名称

        # 构建返回数据
        result = {
            "营业部名称": operate_dept_name,
            "营业部代码": operate_dept_code,
            "机构简称": org_name_abbr,
            "上榜日期": onlist_date_str,
            "买入个股数": buyer_appear_num,
            "卖出个股数": seller_appear_num,
            "总买入金额(万元)": round(total_buy_amt / 10000, 2),
            "总卖出金额(万元)": round(total_sell_amt / 10000, 2),
            "总买卖净额(万元)": round(total_net_amt / 10000, 2),
            "交易股票": buy_stock,
            "股票名称": security_name_abbr,
        }

        return result
