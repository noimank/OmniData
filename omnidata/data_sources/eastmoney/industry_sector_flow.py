"""
东方财富网行业板块资金流 Spider
获取行业板块资金流向排行数据
"""

from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class IndustrySectorFlowParams(BaseModel):
    """行业板块资金流参数模型"""
    limit: int = Field(default=86, ge=1, le=86, description="获取数据条数，最多86条")
    sort_field: Literal["f62", "f2", "f3", "f184"] = Field(
        default="f62",
        description="排序字段：f62=主力净流入, f2=最新价, f3=涨跌幅, f184=主力净占比"
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回格式：json, dict, markdown, string"
    )


class IndustrySectorFlowSpider(BaseWebSpider):
    """行业板块资金流 Spider"""
    name = "eastmoney_industry_sector_flow"
    description = "获取行业板块最新资金流向排行数据"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"
    params_model = IndustrySectorFlowParams

    PAGE_URL = "https://data.eastmoney.com/bkzj/hy.html"
    API_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    FIELDS = "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13"

    async def crawl(self, params: IndustrySectorFlowParams) -> SpiderResult:
        context = await self.get_context_simple("eastmoney")
        page = await context.new_page()
        try:
            await self.apply_anti_detection_scripts(page, "advanced")
            await page.goto(self.PAGE_URL)
            await page.wait_for_load_state("domcontentloaded", timeout=10000)

            # 获取全部数据（2页，每页50条）
            all_items = []
            for page_num in range(1, 3):
                response = await page.request.get(self.API_URL, params={
                    "fid": params.sort_field,
                    "po": "1",
                    "pz": "50",
                    "pn": str(page_num),
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",
                    "fs": "m:90+t:2",
                    "fields": self.FIELDS,
                }, timeout=30000)

                if response.status == 200:
                    data = await response.json()
                    if data.get("rc") == 0:
                        all_items.extend(data.get("data", {}).get("diff", []))

            await page.close()

            # 解析数据
            data_list = [self._parse_item(item) for item in all_items[:params.limit]]
            df = pd.DataFrame(data_list)

            result_data = df.to_dict(orient="records")
            if params.data_format == "markdown":
                result_data = df.to_markdown()
            elif params.data_format == "string":
                result_data = df.to_string()

            return SpiderResult(
                success=True,
                data=result_data,
                message=f"成功获取 {len(data_list)} 条数据"
            )

        except Exception as e:
            return SpiderResult(success=False, message=str(e))
        finally:
            await page.close()
            await context.close()

    def _parse_item(self, item: dict) -> dict:
        def safe_float(v): return float(v) if v not in (None, "") else 0.0

        main_net = safe_float(item.get("f62")) / 100000000

        return {
            "板块代码": item.get("f12", ""),
            "板块名称": item.get("f14", ""),
            "最新价": safe_float(item.get("f2")),
            "涨跌幅(%)": safe_float(item.get("f3")),
            "主力净占比(%)": safe_float(item.get("f184")),
            "主力净流入(亿元)": round(main_net, 2),
            "超大单净流入(亿元)": round(safe_float(item.get("f66")) / 100000000, 2),
            "超大单净占比(%)": safe_float(item.get("f69")),
            "大单净流入(亿元)": round(safe_float(item.get("f72")) / 100000000, 2),
            "大单净占比(%)": safe_float(item.get("f75")),
            "中单净流入(亿元)": round(safe_float(item.get("f78")) / 100000000, 2),
            "中单净占比(%)": safe_float(item.get("f81")),
            "小单净流入(亿元)": round(safe_float(item.get("f84")) / 100000000, 2),
            "小单净占比(%)": safe_float(item.get("f87")),
            "领涨股票": item.get("f204", ""),
            "领涨股票代码": item.get("f205", ""),
            "更新时间": datetime.fromtimestamp(item.get("f124", 0)).strftime("%Y-%m-%d %H:%M:%S") if item.get("f124") else "",
        }
