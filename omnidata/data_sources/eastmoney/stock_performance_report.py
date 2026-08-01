"""
东方财富网股票业绩报表 Spider
获取指定股票的历史业绩报表数据

从 https://data.eastmoney.com/bbsj/yjbb/{stock_code}.html 页面获取数据
通过 datacenter-web 接口获取业绩报表详情
包括营业收入、归母净利润、每股收益、净资产收益率、营业利润率等
"""

import json
import re

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class StockPerformanceReportParams(BaseModel):
    """股票业绩报表参数模型"""

    stock_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="股票代码，如 688313（仕佳光子）、000001（平安银行）",
    )
    page_size: int = Field(default=50, ge=1, le=500, description="每页数据条数，最大500")
    page: int = Field(default=1, ge=1, description="页码，从1开始")


class StockPerformanceReportSpider(BaseWebSpider):
    """
    股票业绩报表 Spider

    从东方财富网获取指定股票的历史业绩报表数据
    包括基本每股收益、扣非每股收益、营业总收入、归母净利润、净资产收益率、
    营业利润率、营收同比增长、净利润同比增长等关键财务指标
    """

    name = "eastmoney_stock_performance_report"
    description = "获取指定股票的历史业绩报表数据，包括每股收益、营收、净利润等关键财务指标"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockPerformanceReportParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    # 业绩报表接口名
    REPORT_NAME = "RPT_LICO_FN_CPD"
    # 入口页面（用于暖手 / Referer）
    ENTRY_URL_TEMPLATE = "https://data.eastmoney.com/bbsj/yjbb/{stock_code}.html"

    async def crawl(self, params: StockPerformanceReportParams) -> SpiderResult:
        """
        爬取股票业绩报表数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        entry_url = self.ENTRY_URL_TEMPLATE.format(stock_code=params.stock_code)

        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # 先访问入口页面，建立 datacenter-web 接口所需的 cookies / Referer 上下文
                await page.goto(entry_url)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    # 即便 domcontentloaded 超时，不影响后续接口调用
                    pass

                # 构建请求参数
                request_params = {
                    "sortColumns": "REPORTDATE",
                    "sortTypes": "-1",
                    "pageSize": str(params.page_size),
                    "pageNumber": str(params.page),
                    "columns": "ALL",
                    "filter": f'(SECURITY_CODE="{params.stock_code}")',
                    "reportName": self.REPORT_NAME,
                }

                # 发送请求（datacenter-web 接口返回 JSONP）
                response = await page.request.get(
                    self.API_URL,
                    params=request_params,
                    headers={"Referer": entry_url},
                    timeout=30000,
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False, message=f"请求失败，状态码：{response.status}"
                    )

                # 获取响应文本（可能是 JSONP 格式，也可能是纯 JSON）
                response_text = await response.text()

                # 解析响应（支持纯 JSON 与 JSONP 两种格式）
                data = self._parse_response(response_text)

                if data is None:
                    return SpiderResult(success=False, message="解析响应数据失败")

                # 检查返回状态
                # API 返回格式: {"version": "...", "result": {"pages": N, "data": [...]}, ...}
                if data.get("result") is None:
                    return SpiderResult(
                        success=False,
                        message=f"接口返回异常：{data.get('message', '未知错误')}",
                    )

                result = data.get("result", {})
                result_list = result.get("data", [])
                if not result_list:
                    return SpiderResult(
                        success=True,
                        data=[],
                        message=f"股票 {params.stock_code} 暂无业绩报表数据",
                    )

                # 解析数据
                parsed_data = self._parse_report_list(result_list)

                if not parsed_data:
                    return SpiderResult(success=False, message="未获取到有效业绩报表数据")

                df = pd.DataFrame(parsed_data)
                # 按报表日期降序排列（最新的在前）
                df = df.sort_values("报表日期", ascending=False).reset_index(drop=True)

                return SpiderResult(
                    success=True,
                    data={
                        "stock_code": params.stock_code,
                        "stock_name": result_list[0].get("SECURITY_NAME_ABBR", ""),
                        "total_pages": result.get("pages", 1),
                        "page": params.page,
                        "page_size": params.page_size,
                        "records": df.to_dict(orient="records"),
                    },
                    message=(
                        f"成功获取股票 {params.stock_code} 的业绩报表数据 "
                        f"共 {len(parsed_data)} 条"
                    ),
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_response(self, response_text: str) -> dict | None:
        """
        解析响应数据（支持纯 JSON 与 JSONP 两种格式）

        Args:
            response_text: 原始响应字符串

        Returns:
            解析后的字典，解析失败返回 None
        """
        stripped = response_text.strip()
        if not stripped:
            return None

        # 优先尝试直接解析为 JSON（datacenter-web 接口实际返回纯 JSON）
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        # 兜底：尝试解析 JSONP 格式（jQuery1123...({...}); 或 callback(...)）
        json_match = re.search(r"jQuery\d+\((.*)\);?", response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                return None

        # 二次兜底：从第一个 '(' 和最后一个 ')' 之间提取
        start_idx = response_text.find("(")
        end_idx = response_text.rfind(")")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(response_text[start_idx + 1 : end_idx])
            except json.JSONDecodeError:
                return None

        return None

    def _parse_report_list(self, data: list[dict]) -> list[dict]:
        """
        解析业绩报表列表数据

        Args:
            data: API 返回的原始数据数组

        Returns:
            解析后的数据列表
        """
        result = []
        for item in data:
            parsed_item = self._parse_single_report(item)
            if parsed_item:
                result.append(parsed_item)
        return result

    def _parse_single_report(self, item: dict) -> dict | None:
        """
        解析单条业绩报表数据

        Args:
            item: API 返回的单条数据

        Returns:
            解析后的数据字典
        """

        def safe_float(value) -> float | None:
            """安全地将值转换为 float，统一保留 4 位小数，无法转换返回 None"""
            if value is None or value == "":
                return None
            try:
                return round(float(value), 4)
            except (ValueError, TypeError):
                return None

        def safe_str(value) -> str:
            """安全地将值转换为字符串"""
            if value is None:
                return ""
            return str(value)

        def yuan_to_yi(value) -> float | None:
            """元 → 亿元，统一保留 4 位小数"""
            if value is None:
                return None
            return round(value / 1e8, 4)

        # 安全提取字符串字段
        security_code = safe_str(item.get("SECURITY_CODE"))
        report_date_raw = safe_str(item.get("REPORTDATE"))
        report_date = report_date_raw[:10] if report_date_raw else ""  # 取 YYYY-MM-DD

        if not security_code or not report_date:
            return None

        # 营业总收入（元 → 亿元，保留 4 位小数）
        total_operate_income = yuan_to_yi(safe_float(item.get("TOTAL_OPERATE_INCOME")))
        # 归属母公司净利润（元 → 亿元，保留 4 位小数）
        parent_netprofit = yuan_to_yi(safe_float(item.get("PARENT_NETPROFIT")))

        # 每股经营现金流（元）
        mgjyxjje = safe_float(item.get("MGJYXJJE"))

        # 净资产收益率（%）
        weightavg_roe = safe_float(item.get("WEIGHTAVG_ROE"))
        # 营业利润率（%）
        xsmll = safe_float(item.get("XSMLL"))

        # 同比增长（%）
        ystz = safe_float(item.get("YSTZ"))  # 营业总收入同比
        sjltz = safe_float(item.get("SJLTZ"))  # 归属母公司净利润同比

        # 环比增长（%）
        yshz = safe_float(item.get("YSHZ"))  # 营业总收入环比
        sjhhz = safe_float(item.get("SJLHZ"))  # 归属母公司净利润环比

        result = {
            "股票代码": security_code,
            "股票简称": safe_str(item.get("SECURITY_NAME_ABBR")),
            "报表日期": report_date,
            "公告日期": safe_str(item.get("NOTICE_DATE"))[:10] if item.get("NOTICE_DATE") else "",
            "报告类型": safe_str(item.get("DATATYPE")),
            "数据日期": safe_str(item.get("QDATE")),
            "交易所": safe_str(item.get("TRADE_MARKET")),
            "所属行业": safe_str(item.get("BOARD_NAME")),
            "基本每股收益(元)": safe_float(item.get("BASIC_EPS")),
            "扣非每股收益(元)": safe_float(item.get("DEDUCT_BASIC_EPS")),
            "每股净资产(元)": safe_float(item.get("BPS")),
            "每股经营现金流(元)": mgjyxjje,
            "营业总收入(亿元)": total_operate_income,
            "归属母公司净利润(亿元)": parent_netprofit,
            "加权净资产收益率(%)": weightavg_roe,
            "营业利润率(%)": xsmll,
            "营业总收入同比增长(%)": ystz,
            "净利润同比增长(%)": sjltz,
            "营业总收入季度环比增长(%)": yshz,
            "净利润季度环比增长(%)": sjhhz,
            "利润分配方案": safe_str(item.get("ASSIGNDSCRPT")),
        }

        # 去除全部字段为 None 的报表记录
        meaningful_values = [
            result["基本每股收益(元)"],
            result["扣非每股收益(元)"],
            result["每股净资产(元)"],
            result["每股经营现金流(元)"],
            result["营业总收入(亿元)"],
            result["归属母公司净利润(亿元)"],
            result["加权净资产收益率(%)"],
            result["营业利润率(%)"],
        ]
        if all(v is None for v in meaningful_values):
            return None

        return result
