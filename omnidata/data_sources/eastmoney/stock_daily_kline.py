"""
东方财富网股票日线数据 Spider
获取A股个股的历史日线K线数据

从 https://push2his.eastmoney.com/api/qt/stock/kline/get 接口获取数据
支持查询前复权、后复权、不复权等多种K线类型
"""

import random
import re
import time
from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class StockDailyKlineParams(BaseModel):
    """股票日线K线参数模型"""

    stock_code: str = Field(
        ...,
        min_length=6, max_length=6,
        description="股票代码，6位数字，例如：000001(平安银行)、600000(浦发银行)"
    )
    start_date: str = Field(
        default="19900101",
        pattern=r"^\d{8}$",
        description="开始日期，格式：yyyyMMdd，例如：20200101，默认19900101"
    )
    end_date: str = Field(
        default="20500101",
        pattern=r"^\d{8}$",
        description="结束日期，格式：yyyyMMdd，例如：20251231，默认20500101"
    )
    adjust_type: Literal["qfq", "hfq", "none"] = Field(
        default="qfq",
        description="复权类型，可选值：qfq(前复权)、hfq(后复权)、none(不复权)，默认前复权"
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, string, markdown"
    )


class StockDailyKlineSpider(BaseWebSpider):
    """
    股票日线K线 Spider

    从东方财富网获取A股个股的历史日线K线数据
    包括日期、开盘价、收盘价、最高价、最低价、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
    支持前复权、后复权、不复权三种复权方式
    """

    name = "eastmoney_stock_daily_kline"
    description = "获取A股个股历史日线K线数据，包括开高低收、成交量成交额、涨跌幅等完整K线数据，支持前复权/后复权/不复权，支持日期范围查询"
    version = "1.1.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockDailyKlineParams

    # API 配置
    API_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    # 复权类型映射
    ADJUST_TYPE_MAP = {
        "qfq": "1",  # 前复权
        "hfq": "2",  # 后复权
        "none": "0",  # 不复权
    }

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

    async def crawl(self, params: StockDailyKlineParams) -> SpiderResult:
        """
        爬取股票日线K线数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        context = await self.get_context_simple("eastmoney")
        page = await context.new_page()
        try:
            await self.apply_anti_detection_scripts(page, "advanced")
            # 根据股票代码自动判断市场ID
            # 6开头 = 上海市场(1), 0/3开头 = 深圳市场(0), 8开头 = 北交所(2)
            stock_code = params.stock_code
            if stock_code.startswith("6"):
                market_id = "1"  # 上海
            elif stock_code.startswith("8"):
                market_id = "2"  # 北交所
            else:
                market_id = "0"  # 深圳

            secid = f"{market_id}.{stock_code}"

            # 构建请求参数
            request_params = {
                "cb": self._generate_jsonp_callback(),  # 动态生成 JSONP 回调函数名
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                # "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "ut": "b2884a393a59ad64002292a3e90d46a5",
                "klt": "101",  # 101表示日线
                "fqt": self.ADJUST_TYPE_MAP[params.adjust_type],
                "secid": secid,
                "beg": params.start_date,
                "end": params.end_date,
                "_": str(int(time.time() * 1000)),  # 添加时间戳参数
            }

            await self.apply_anti_detection_scripts(page, "advanced")

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
            # 例如：jQuery112304786753408034462_1768642295465({...});
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

            # 检查返回状态
            if data.get("rc") != 0:
                return SpiderResult(
                    success=False,
                    message=f"获取数据失败：{data.get('rt', '未知错误')}"
                )

            # 检查是否有数据
            kline_data = data.get("data", {})
            if not kline_data or not kline_data.get("klines"):
                return SpiderResult(
                    success=False,
                    message=f"未找到股票代码 {params.stock_code} 的K线数据，请检查股票代码是否正确"
                )

            # 解析数据
            result_data = self._parse_klines(kline_data)

            # 转换为 DataFrame 并按日期升序排列（最早的在前）
            df = pd.DataFrame(result_data)
            df = df.sort_values("日期", ascending=True).reset_index(drop=True)

            # 获取股票名称
            stock_name = kline_data.get("name", params.stock_code)

            # 获取复权类型名称
            adjust_name = self._get_adjust_name(params.adjust_type)

            # 格式化输出
            if params.data_format == "markdown":
                return SpiderResult(
                    success=True,
                    data=df.to_markdown(),
                    message=f"成功获取 {stock_name}({params.stock_code}) {adjust_name}日线K线数据，共{len(result_data)}条"
                )
            if params.data_format == "string":
                return SpiderResult(
                    success=True,
                    data=df.to_string(),
                    message=f"成功获取 {stock_name}({params.stock_code}) {adjust_name}日线K线数据，共{len(result_data)}条"
                )

            # 默认返回 dict 格式
            return SpiderResult(
                success=True,
                data=df.to_dict(orient="records"),
                message=f"成功获取 {stock_name}({params.stock_code}) {adjust_name}日线K线数据，共{len(result_data)}条"
            )

        except Exception as e:
            return SpiderResult(
                success=False,
                message=f"爬取失败：{str(e)}"
            )
        finally:
            await page.close()
            await context.close()

    def _get_adjust_name(self, adjust_type: str) -> str:
        """获取复权类型显示名称"""
        names = {
            "qfq": "前复权",
            "hfq": "后复权",
            "none": "不复权",
        }
        return names.get(adjust_type, "前复权")

    def _parse_klines(self, kline_data: dict) -> list[dict]:
        """
        解析K线数据

        Args:
            kline_data: API返回的K线数据对象

        Returns:
            解析后的数据列表
        """
        result = []
        klines = kline_data.get("klines", [])

        for kline_str in klines:
            parsed_item = self._parse_single_kline(kline_str)
            if parsed_item:
                result.append(parsed_item)

        return result

    def _parse_single_kline(self, kline_str: str) -> dict | None:
        """
        解析单条K线数据

        Args:
            kline_str: K线字符串，格式：日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
            例如：2025-08-20,46.17,47.58,48.63,45.47,2530587,11955177840.00,6.50,-2.06,-1.00,1.27

        Returns:
            解析后的数据字典
        """

        def safe_float(value) -> float:
            """安全地将值转换为 float"""
            if value is None or value == "" or value == "-":
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0

        def safe_int(value) -> int:
            """安全地将值转换为 int"""
            if value is None or value == "" or value == "-":
                return 0
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return 0

        # 分割字符串
        parts = kline_str.split(",")

        if len(parts) < 11:
            return None

        # 解析各字段
        # 日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
        date_str = parts[0]  # 日期
        open_price = safe_float(parts[1])  # 开盘价
        close_price = safe_float(parts[2])  # 收盘价
        high_price = safe_float(parts[3])  # 最高价
        low_price = safe_float(parts[4])  # 最低价
        volume = safe_int(parts[5])  # 成交量（手）
        amount = safe_float(parts[6])  # 成交额（元）
        amplitude = safe_float(parts[7])  # 振幅(%)
        change_percent = safe_float(parts[8])  # 涨跌幅(%)
        change_amount = safe_float(parts[9])  # 涨跌额
        turnover_rate = safe_float(parts[10]) if len(parts) > 10 else 0.0  # 换手率(%)

        # 构建返回数据
        result = {
            "日期": date_str,
            "开盘": round(open_price, 2),
            "收盘": round(close_price, 2),
            "最高": round(high_price, 2),
            "最低": round(low_price, 2),
            "成交量(手)": volume,
            "成交额(万元)": round(amount / 10000, 2),
            "振幅(%)": round(amplitude, 2),
            "涨跌幅(%)": round(change_percent, 2),
            "涨跌额": round(change_amount, 2),
            "换手率(%)": round(turnover_rate, 2),
        }

        return result
