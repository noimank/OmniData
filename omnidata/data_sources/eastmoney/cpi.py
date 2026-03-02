"""
东方财富网中国CPI居民消费价格指数 Spider
获取中国居民消费价格指数月度数据

从 https://data.eastmoney.com/cpi.html 页面获取数据
支持获取全国、城市、农村的CPI当月、同比增长、环比增长、累计数据
"""

from pydantic import BaseModel, Field
from typing import Literal

from omnidata.core import BaseWebSpider, SpiderResult


class CPIParams(BaseModel):
    """CPI居民消费价格指数参数模型"""

    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="每页数量，默认200条，最大500条",
    )


class CPISpider(BaseWebSpider):
    """
    中国CPI居民消费价格指数 Spider

    从东方财富网获取中国居民消费价格指数月度数据
    包括全国、城市、农村的当月同比、环比增长及累计数据
    """

    name = "eastmoney_china_cpi"
    description = (
        "获取中国CPI居民消费价格指数月度数据，包括全国、城市、农村的当月同比、环比增长及累计数据"
    )
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = CPIParams

    API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    COLUMNS = "REPORT_DATE,TIME,NATIONAL_SAME,NATIONAL_BASE,NATIONAL_SEQUENTIAL,NATIONAL_ACCUMULATE,CITY_SAME,CITY_BASE,CITY_SEQUENTIAL,CITY_ACCUMULATE,RURAL_SAME,RURAL_BASE,RURAL_SEQUENTIAL,RURAL_ACCUMULATE"

    async def crawl(self, params: CPIParams) -> SpiderResult:
        """
        爬取CPI居民消费价格指数数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                # 构建请求参数
                request_params = {
                    "callback": "datatable5402973",
                    "columns": self.COLUMNS,
                    "pageNumber": "1",
                    "pageSize": str(params.limit),
                    "sortColumns": "REPORT_DATE",
                    "sortTypes": "-1",
                    "source": "WEB",
                    "client": "WEB",
                    "reportName": "RPT_ECONOMY_CPI",
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
                text = await response.text()

                # 处理JSONP响应
                # 响应格式：datatable5402973({...});
                if not text.startswith("datatable5402973("):
                    return SpiderResult(success=False, message=f"响应格式错误：{text[:100]}")

                import json

                # 移除 callback 前缀和结尾的 });
                if text.endswith("});"):
                    json_str = text[17:-2]
                else:
                    json_str = text[17:-1]

                data = json.loads(json_str)

                # 检查返回状态
                if data.get("code") != 0:
                    return SpiderResult(
                        success=False, message=f"获取数据失败：{data.get('message', '未知错误')}"
                    )

                # 检查是否有数据
                result_data = data.get("result", {})
                items = result_data.get("data", [])

                if not items:
                    return SpiderResult(success=False, message="未找到CPI数据")

                # 解析数据
                parsed_data = [self._parse_cpi(item) for item in items]

                return SpiderResult(
                    success=True, data=parsed_data, message=f"成功获取 {len(parsed_data)} 条CPI数据"
                )
        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_cpi(self, item: dict) -> dict:
        """
        解析CPI数据

        Args:
            item: API返回的单条数据

        Returns:
            解析后的数据字典
        """

        def safe_float(value) -> float | None:
            """安全地将值转换为 float"""
            if value is None or value == "" or value == "-":
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        def safe_str(value) -> str:
            """安全地将值转换为 str"""
            if value is None:
                return ""
            return str(value)

        # 报告日期
        report_date = safe_str(item.get("REPORT_DATE"))
        time_str = safe_str(item.get("TIME"))

        # 全国数据
        national_same = safe_float(item.get("NATIONAL_SAME"))  # 同比增长
        national_base = safe_float(item.get("NATIONAL_BASE"))  # 当月
        national_sequential = safe_float(item.get("NATIONAL_SEQUENTIAL"))  # 环比增长
        national_accumulate = safe_float(item.get("NATIONAL_ACCUMULATE"))  # 累计

        # 城市数据
        city_same = safe_float(item.get("CITY_SAME"))  # 同比增长
        city_base = safe_float(item.get("CITY_BASE"))  # 当月
        city_sequential = safe_float(item.get("CITY_SEQUENTIAL"))  # 环比增长
        city_accumulate = safe_float(item.get("CITY_ACCUMULATE"))  # 累计

        # 农村数据
        rural_same = safe_float(item.get("RURAL_SAME"))  # 同比增长
        rural_base = safe_float(item.get("RURAL_BASE"))  # 当月
        rural_sequential = safe_float(item.get("RURAL_SEQUENTIAL"))  # 环比增长
        rural_accumulate = safe_float(item.get("RURAL_ACCUMULATE"))  # 累计

        # 构建返回数据
        result = {
            "月份": time_str or report_date,
            "全国": {
                "当月": national_base,
                "同比增长(%)": national_same,
                "环比增长(%)": national_sequential,
                "累计": national_accumulate,
            },
            "城市": {
                "当月": city_base,
                "同比增长(%)": city_same,
                "环比增长(%)": city_sequential,
                "累计": city_accumulate,
            },
            "农村": {
                "当月": rural_base,
                "同比增长(%)": rural_same,
                "环比增长(%)": rural_sequential,
                "累计": rural_accumulate,
            },
        }

        return result
