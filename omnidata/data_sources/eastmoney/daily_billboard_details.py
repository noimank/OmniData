"""
东方财富网龙虎榜详情 Spider
获取指定日期范围的龙虎榜交易明细数据

从 https://data.eastmoney.com/lhb/ 页面获取龙虎榜数据
包括上榜股票、涨跌幅、龙虎榜净买入金额、成交金额等数据
"""

from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class DailyBillboardDetailsParams(BaseModel):
    """龙虎榜详情参数模型"""

    start_date: str = Field(default="", description="开始日期，格式：YYYY-MM-DD，如 2026-01-14，默认为当天")
    end_date: str = Field(default="", description="结束日期，格式：YYYY-MM-DD，如 2026-01-16，默认为当天")
    limit: int = Field(default=100, ge=1, le=1000, description="获取数据条数，最多1000条")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, string, markdown"
    )


class DailyBillboardDetailsSpider(BaseWebSpider):
    """
    龙虎榜详情 Spider

    从东方财富网获取指定日期范围的龙虎榜交易明细数据
    包括上榜股票、涨跌幅、龙虎榜买卖金额、净买入金额、成交金额占比等
    """

    name = "eastmoney_daily_billboard_details"
    description = "获取指定日期范围的龙虎榜交易明细数据，包括上榜股票、涨跌幅、龙虎榜买卖金额等"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = DailyBillboardDetailsParams

    # API 配置
    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    # 字段列表
    COLUMNS = (
        "SECURITY_CODE,SECUCODE,SECURITY_NAME_ABBR,TRADE_DATE,EXPLAIN,"
        "CLOSE_PRICE,CHANGE_RATE,BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,"
        "BILLBOARD_DEAL_AMT,ACCUM_AMOUNT,DEAL_NET_RATIO,DEAL_AMOUNT_RATIO,TURNOVERRATE,"
        "FREE_MARKET_CAP,EXPLANATION,D1_CLOSE_ADJCHRATE,D2_CLOSE_ADJCHRATE,D5_CLOSE_ADJCHRATE,"
        "D10_CLOSE_ADJCHRATE,SECURITY_TYPE_CODE"
    )

    async def crawl(self, params: DailyBillboardDetailsParams) -> SpiderResult:
        """
        爬取龙虎榜详情数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        context = await self.get_context_simple("eastmoney")
        page = await context.new_page()
        try:
            await self.apply_anti_detection_scripts(page, "advanced")

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
                    success=False,
                    message="日期格式错误，请使用 YYYY-MM-DD 格式，如 2026-01-14"
                )

            # 构建过滤条件
            filter_str = f"(TRADE_DATE<='{end_date}')(TRADE_DATE>='{start_date}')"

            # 分页请求获取数据
            all_data = []
            page_number = 1
            page_size = 100  # 每页固定100条
            total = 0
            pages = 0

            while len(all_data) < params.limit:
                # 构建请求参数
                request_params = {
                    "sortColumns": "SECURITY_CODE,TRADE_DATE",
                    "sortTypes": "1,-1",
                    "pageSize": str(page_size),
                    "pageNumber": str(page_number),
                    "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                    "columns": self.COLUMNS,
                    "source": "WEB",
                    "client": "WEB",
                    "filter": filter_str,
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
                            message=f"获取数据失败，请检查日期范围是否正确"
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
                    message=f"指定日期范围 {start_date} 至 {end_date} 无龙虎榜数据"
                )

            # 截取到指定数量
            all_data = all_data[:params.limit]

            # 解析数据
            result_data = self._parse_billboard_data(all_data)

            # 按日期和股票代码排序
            df = pd.DataFrame(result_data)
            # df = df.sort_values(["上榜日期", "股票代码"], ascending=[False, True]).reset_index(drop=True)

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
                    message=f"成功获取龙虎榜数据（共 {len(result_data)} 条，总计 {total} 条）"
                )
            if params.data_format == "string":
                return SpiderResult(
                    success=True,
                    data={
                        "stats": stats_info,
                        "records": df.to_string(),
                    },
                    message=f"成功获取龙虎榜数据（共 {len(result_data)} 条，总计 {total} 条）"
                )

            # 默认返回 dict 格式
            return SpiderResult(
                success=True,
                data={
                    "stats": stats_info,
                    "records": df.to_dict(orient="records"),
                },
                message=f"成功获取龙虎榜数据（共 {len(result_data)} 条，总计 {total} 条）"
            )

        except Exception as e:
            return SpiderResult(
                success=False,
                message=f"爬取失败：{str(e)}"
            )
        finally:
            await page.close()
            await context.close()

    def _parse_billboard_data(self, data: list) -> list[dict]:
        """
        解析龙虎榜数据

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
        解析单条龙虎榜数据

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
        trade_date_str = item.get("TRADE_DATE", "")[:10] if item.get("TRADE_DATE") else ""  # 上榜日期
        security_code = safe_str(item.get("SECURITY_CODE"))  # 股票代码
        secucode = safe_str(item.get("SECUCODE"))  # 证券代码
        security_name = safe_str(item.get("SECURITY_NAME_ABBR"))  # 股票名称
        security_type_code = safe_str(item.get("SECURITY_TYPE_CODE"))  # 证券类型代码

        # 价格相关
        close_price = safe_float(item.get("CLOSE_PRICE"))  # 收盘价
        change_rate = safe_float(item.get("CHANGE_RATE"))  # 涨跌幅

        # 龙虎榜金额相关（单位：元）
        billboard_net_amt = safe_float(item.get("BILLBOARD_NET_AMT"))  # 龙虎榜净买入金额
        billboard_buy_amt = safe_float(item.get("BILLBOARD_BUY_AMT"))  # 龙虎榜买入金额
        billboard_sell_amt = safe_float(item.get("BILLBOARD_SELL_AMT"))  # 龙虎榜卖出金额
        billboard_deal_amt = safe_float(item.get("BILLBOARD_DEAL_AMT"))  # 龙虎榜成交金额
        accum_amount = safe_float(item.get("ACCUM_AMOUNT"))  # 市场总成交额

        # 比率相关
        deal_net_ratio = safe_float(item.get("DEAL_NET_RATIO"))  # 龙虎榜净买入占市场成交比
        deal_amount_ratio = safe_float(item.get("DEAL_AMOUNT_RATIO"))  # 龙虎榜成交额占市场成交比
        turnoverrate = safe_float(item.get("TURNOVERRATE"))  # 换手率
        free_market_cap = safe_float(item.get("FREE_MARKET_CAP"))  # 流通市值

        # 上榜原因
        explain = safe_str(item.get("EXPLAIN"))  # 上榜原因（简短版）
        explanation = safe_str(item.get("EXPLANATION"))  # 上榜原因（详细版）

        # 上榜后涨跌幅
        d1_close_adjchrate = safe_float(item.get("D1_CLOSE_ADJCHRATE"))  # 上榜后1日
        d2_close_adjchrate = safe_float(item.get("D2_CLOSE_ADJCHRATE"))  # 上榜后2日
        d5_close_adjchrate = safe_float(item.get("D5_CLOSE_ADJCHRATE"))  # 上榜后5日
        d10_close_adjchrate = safe_float(item.get("D10_CLOSE_ADJCHRATE"))  # 上榜后10日

        # 构建返回数据
        result = {
            "股票代码": security_code,
            "证券代码": secucode,
            "股票名称": security_name,
            "证券类型": security_type_code,
            "上榜日期": trade_date_str,
            "收盘价": round(close_price, 2),
            "涨跌幅(%)": round(change_rate, 2),
            "龙虎榜净买入(万元)": round(billboard_net_amt / 10000, 2),
            "龙虎榜买入金额(万元)": round(billboard_buy_amt / 10000, 2),
            "龙虎榜卖出金额(万元)": round(billboard_sell_amt / 10000, 2),
            "龙虎榜成交金额(万元)": round(billboard_deal_amt / 10000, 2),
            "市场总成交额(万元)": round(accum_amount / 10000, 2),
            "净买入占成交比(%)": round(deal_net_ratio, 2),
            "龙虎榜成交额占比(%)": round(deal_amount_ratio, 2),
            "换手率(%)": round(turnoverrate, 2),
            "流通市值(亿元)": round(free_market_cap / 100000000, 2),
            "上榜原因": explain or explanation,
            "上榜后1日涨跌幅(%)": round(d1_close_adjchrate, 2),
            "上榜后2日涨跌幅(%)": round(d2_close_adjchrate, 2),
            "上榜后5日涨跌幅(%)": round(d5_close_adjchrate, 2),
            "上榜后10日涨跌幅(%)": round(d10_close_adjchrate, 2),
        }

        return result
