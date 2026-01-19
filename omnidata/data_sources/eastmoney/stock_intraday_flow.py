"""
东方财富网个股分时资金流 Spider
获取个股分时资金流向数据（分钟级别）

从东方财富网API直接获取数据
接口地址：https://push2.eastmoney.com/api/qt/stock/fflow/kline/get
"""

import json
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class StockIntradayFlowParams(BaseModel):
    """个股分时资金流参数模型"""

    stock_code: str = Field(..., min_length=6, max_length=6, description="股票或ETF代码，如 000001（平安银行）、516920（芯片ETF）")
    limit: int = Field(default=0, ge=0, le=500, description="获取最近多少条分时数据，0表示全部")
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, string, markdown"
    )


class StockIntradayFlowSpider(BaseWebSpider):
    """
    个股分时资金流 Spider

    从东方财富网API直接获取个股分时资金流向数据（分钟级别）
    返回 DataFrame 格式的表格数据
    """

    name = "eastmoney_stock_intraday_flow"
    description = "获取个股/ETF分时资金流向数据（分钟级别），包括主力、超大单、大单、中单、小单的净流入"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockIntradayFlowParams

    # API 配置
    API_URL = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    FIELDS1 = "f1,f2,f3,f7"
    FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"

    async def crawl(self, params: StockIntradayFlowParams) -> SpiderResult:
        """
        爬取个股分时资金流数据

        数据来源：东方财富网API
        通过直接请求API获取个股分时资金流向数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            # 判断股票所属市场
            # 上海市场：600xxx, 601xxx, 603xxx, 605xxx, 688xxx
            # 深圳市场：000xxx, 001xxx, 002xxx, 003xxx, 300xxx, 301xxx
            first_char = params.stock_code[0]

            if first_char == "6" or first_char == "5":
                market_code = "1"  # 上海市场
            else:
                market_code = "0"  # 深圳市场

            secid = f"{market_code}.{params.stock_code}"

            async with self.new_page("eastmoney") as page:
                # 构建请求参数
                request_params = {
                "lmt": params.limit if params.limit > 0 else 0,
                "klt": "1",  # 分时K线（1=分时，101=日K）
                "fields1": self.FIELDS1,
                "fields2": self.FIELDS2,
                "ut": "b2884a393a59ad64002292a3e90d46a5",
                "secid": secid}

                # 发送请求
                response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

                if response.status != 200:
                    return SpiderResult(
                        success=False,
                        message=f"请求失败，状态码：{response.status}"
                    )

                # 解析响应（可能是JSONP格式）
                body = await response.body()
                data = self._parse_response(body)

                if data is None:
                    return SpiderResult(
                        success=False,
                        message="解析响应数据失败"
                    )

                # 检查返回状态
                if data.get("rc") != 0:
                    return SpiderResult(
                        success=False,
                        message=f"获取数据失败，请检查股票代码是否存在！"
                    )

                # 获取数据内容
                klines = data.get("data", {}).get("klines", [])

                if not klines:
                    return SpiderResult(
                        success=False,
                        message=f"未找到股票代码 {params.stock_code} 的分时资金流数据"
                    )

                # 解析 K线数据（逗号分隔的字符串）
                klines = [line.split(",") for line in klines]

                # 构建数据列表
                data_list = []

                for kline in klines:
                    if len(kline) >= 6:
                        datetime_str = kline[0]  # 格式: "2026-01-16 09:31"

                        # 解析数值
                        # 根据历史资金流的字段对应关系：
                        # f51=主力净流入净额, f52=小单净流入净额, f53=中单净流入净额
                        # f54=大单净流入净额, f55=超大单净流入净额
                        main_net_amount = self._safe_float(kline[1])      # 主力净流入（元）
                        small_net_amount = self._safe_float(kline[2])     # 小单净流入（元）
                        medium_net_amount = self._safe_float(kline[3])    # 中单净流入（元）
                        large_net_amount = self._safe_float(kline[4])     # 大单净流入（元）
                        super_large_net_amount = self._safe_float(kline[5])  # 超大单净流入（元）

                        data_list.append({
                            "时间": datetime_str,
                            "主力净流入(万元)": round(main_net_amount / 10000, 2),
                            "超大单净流入(万元)": round(super_large_net_amount / 10000, 2),
                            "大单净流入(万元)": round(large_net_amount / 10000, 2),
                            "中单净流入(万元)": round(medium_net_amount / 10000, 2),
                            "小单净流入(万元)": round(small_net_amount / 10000, 2),
                        })

                # 转换为 DataFrame
                df = pd.DataFrame(data_list)

                # 按时间降序排列（最新的在前）
                df = df.sort_values("时间", ascending=False).reset_index(drop=True)

                # 如果用户指定了限制条数且大于0
                if params.limit > 0 and len(df) > params.limit:
                    df = df.head(params.limit)

                result_data = df.to_dict(orient="records")
                if params.data_format == "markdown":
                    result_data = df.to_markdown()
                elif params.data_format == "string":
                    result_data = df.to_string()

                return SpiderResult(
                    success=True,
                    data=result_data,
                    message=f"成功获取股票代码 {params.stock_code} 的分时资金流数据共{len(df)}条"
                )

        except Exception as e:
            return SpiderResult(
                success=False,
                message=f"爬取失败：{str(e)}"
            )

    def _parse_response(self, body: bytes) -> dict | None:
        """
        解析响应数据（支持JSON和JSONP格式）

        Args:
            body: 响应体字节数据

        Returns:
            解析后的字典，解析失败返回 None
        """
        try:
            text = body.decode("utf-8")

            # 尝试直接解析JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

            # 如果是JSONP格式，提取JSON数据
            # 格式：jQuery1234567890({...}) 或 callback({...})
            start_idx = text.find("(")
            end_idx = text.rfind(")")
            if start_idx > 0 and end_idx > start_idx:
                json_text = text[start_idx + 1:end_idx]
                return json.loads(json_text)

            return None
        except Exception:
            return None

    @staticmethod
    def _safe_float(value: str | int | float | None) -> float:
        """安全地将值转换为 float"""
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
