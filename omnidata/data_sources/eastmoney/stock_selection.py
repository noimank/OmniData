"""
东方财富网条件选股 Spider
通过自然语言查询获取选股结果数据

API 接口: https://np-tjxg-g.eastmoney.com/api/smart-tag/stock/v3/pw/search-code
支持自然语言查询，动态返回字段
"""

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class StockSelectionParams(BaseModel):
    """条件选股参数模型"""

    query_text: str = Field(
        ...,
        description="选股条件文本，例如：换手率介于5%~10%;涨跌幅大于3%",
        alias="queryText",
    )
    page_num: int = Field(default=1, ge=1, description="页码，从1开始", alias="pageNo")
    page_size: int = Field(
        default=50, ge=1, le=500, description="每页数量，默认50，最大500", alias="pageSize"
    )

    model_config = {"populate_by_name": True}


class StockSelectionSpider(BaseWebSpider):
    """
    东方财富条件选股 Spider

    通过自然语言查询获取选股结果数据。

    使用示例:
        query_text="换手率大于5%"
        query_text="涨停;流通市值小于50亿"
        query_text="5日均线大于10日均线;成交量大于100万手"

    返回字段根据选股条件动态变化，常见字段包括：
    - 股票代码、股票名称、市场
    - 最新价、涨跌幅、涨跌额
    - 成交量、成交额、换手率
    - 市盈率、市净率、市值等
    """

    name = "eastmoney_stock_selection"
    description = "东方财富条件选股，通过自然语言查询获取符合条件的股票列表"
    version = "2.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockSelectionParams

    # API 配置
    API_URL = "https://np-tjxg-g.eastmoney.com/api/smart-tag/stock/v3/pw/search-code"

    def _generate_request_id(self) -> str:
        """生成随机请求ID"""
        random_uuid = uuid.uuid4().hex
        timestamp = str(int(time.time() * 1000))
        return f"{random_uuid[:24]}{timestamp}"

    def _generate_fingerprint(self) -> str:
        """生成浏览器指纹"""
        return uuid.uuid4().hex

    def _parse_value(self, value: Any, is_code_field: bool = False) -> Any:
        """智能解析值，处理带单位的数值"""
        if value is None or value == "":
            return None

        if isinstance(value, (int, float)):
            # 如果是代码字段，转换为字符串保持前导零
            if is_code_field:
                return str(int(value)).zfill(6)
            return value

        if isinstance(value, str):
            # 代码字段直接返回字符串
            if is_code_field:
                return value.strip()

            # 尝试解析带单位的数值
            value_str = value.strip()
            original = value_str

            # 记录单位
            unit = ""
            if "亿" in value_str:
                unit = "亿"
                value_str = value_str.replace("亿", "")
            elif "万" in value_str:
                unit = "万"
                value_str = value_str.replace("万", "")
            elif "%" in value_str:
                unit = "%"
                value_str = value_str.replace("%", "")

            # 尝试转换为数值
            try:
                if "." in value_str:
                    num = float(value_str)
                else:
                    num = int(value_str)

                # 返回带单位的字符串或纯数值
                return f"{num}{unit}" if unit else num
            except ValueError:
                # 无法转换为数值，返回原始字符串
                return original

        return value

    def _parse_response(self, data: dict, query_text: str) -> dict:
        """
        动态解析选股结果数据

        根据返回的 columns 动态映射字段，支持不同选股条件返回不同字段

        Args:
            data: API返回的数据
            query_text: 选股条件文本

        Returns:
            解析后的数据字典
        """
        result_data = data.get("data", {}).get("result", {})

        # 获取列定义
        columns = result_data.get("columns", [])

        # 构建字段映射：key -> title
        field_mapping = {}
        for col in columns:
            key = col.get("key", "")
            title = col.get("title", "")
            if key and title:
                field_mapping[key] = title

        # 识别代码字段（SECURITY_CODE）
        code_keys = {"SECURITY_CODE", "CODE", "股票代码"}

        # 解析数据列表
        stocks = []
        for item in result_data.get("dataList", []):
            stock = {}
            # 遍历所有字段，使用中文标题作为键
            for key, title in field_mapping.items():
                raw_value = item.get(key)
                # 判断是否为代码字段
                is_code = key in code_keys or "代码" in title
                stock[title] = self._parse_value(raw_value, is_code_field=is_code)

            stocks.append(stock)

        # 获取分页信息
        meta = result_data.get("meta", {})

        return {
            "选股条件": query_text,
            # "xcId": data.get("data", {}).get("xcId", ""),
            "total_count": result_data.get("total", 0),
            "current_page": meta.get("pageNum", 1),
            "page_size": meta.get("pageSize", 50),
            # "columns": [col.get("title", "") for col in columns],  # 返回列名列表
            "stocks": stocks,
        }

    async def crawl(self, params: StockSelectionParams) -> SpiderResult:
        """
        爬取条件选股数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                # 先访问选股页面设置必要的 cookies
                await page.goto("https://xuangu.eastmoney.com/", wait_until="networkidle")

                # 构建请求体
                timestamp = str(int(time.time() * 1000)) + "421"
                request_body = {
                    "needAmbiguousSuggest": True,
                    "pageSize": params.page_size,
                    "pageNo": params.page_num,
                    "fingerprint": self._generate_fingerprint(),
                    "matchWord": "",
                    "shareToGuba": False,
                    "timestamp": timestamp,
                    "requestId": self._generate_request_id(),
                    "removedConditionIdList": [],
                    "ownSelectAll": False,
                    "needCorrect": True,
                    "client": "WEB",
                    "product": "",
                    "needShowStockNum": False,
                    "biz": "web_ai_select_stocks",
                    "gids": [],
                    "dxInfoNew": [],
                    "keyWordNew": params.query_text,
                    "customDataNew": f'[{{"type":"text","value":"{params.query_text}","extra":""}}]',
                }

                # 设置请求头
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/plain, */*",
                    "curPage": "stockResult",
                    "jumpSource": "api",
                }

                # 发送 POST 请求
                response = await page.request.post(
                    self.API_URL, data=request_body, headers=headers, timeout=30000
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False, message=f"请求失败，状态码：{response.status}"
                    )

                # 解析响应
                data = await response.json()

                # 检查返回状态
                if data.get("code") != "100":
                    return SpiderResult(
                        success=False, message=f"获取数据失败：{data.get('msg', '未知错误')}"
                    )

                # 解析数据
                result_data = self._parse_response(data, params.query_text)

                return SpiderResult(
                    success=True,
                    data=result_data,
                    message=f"成功获取选股结果，共 {result_data['total_count']} 条，"
                    f"当前第 {params.page_num} 页，返回 {len(result_data['stocks'])} 条",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")
