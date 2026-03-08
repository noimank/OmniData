"""
东方财富网行业板块个股资金流 Spider
获取指定行业板块内个股的资金流向排行数据
"""

from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class SectorStockFlowParams(BaseModel):
    """行业板块个股资金流参数模型"""

    sector_code: str = Field(..., description="板块代码,如 BK0737")
    limit: int = Field(default=50, ge=1, le=150, description="获取数据条数,最多150条")
    rank_type: Literal["today", "5day", "10day"] = Field(
        default="today", description="排行类型:today=今日排行, 5day=5日排行, 10day=10日排行"
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回格式:json, dict, markdown, string"
    )


class SectorStockFlowSpider(BaseWebSpider):
    """行业板块个股资金流 Spider"""

    name = "eastmoney_sector_stock_flow"
    description = "获取指定行业板块内个股的资金流向排行数据"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"
    params_model = SectorStockFlowParams

    PAGE_URL = "https://data.eastmoney.com/bkzj/{sector_code}.html"
    API_URL = "https://push2.eastmoney.com/api/qt/clist/get"

    # 不同排行类型的配置
    RANK_CONFIG = {
        "today": {
            "fid": "f62",
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13",
        },
        "5day": {
            "fid": "f164",
            "fields": "f12,f14,f2,f109,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f257,f258,f124,f1,f13",
        },
        "10day": {
            "fid": "f174",
            "fields": "f12,f14,f2,f160,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f260,f261,f124,f1,f13",
        },
    }

    async def crawl(self, params: SectorStockFlowParams) -> SpiderResult:
        try:
            # 获取对应排行类型的配置
            config = self.RANK_CONFIG[params.rank_type]

            async with self.new_page("eastmoney") as page:
                await self.apply_anti_detection_scripts(page, "advanced")
                page_url = self.PAGE_URL.format(sector_code=params.sector_code)
                await page.goto(page_url)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)

                # 获取全部数据(分页获取,每页50条)
                all_items = []
                pages_needed = (params.limit + 49) // 50  # 向上取整

                for page_num in range(1, pages_needed + 1):
                    response = await page.request.get(
                        self.API_URL,
                        params={
                            "fid": config["fid"],
                            "po": "1",
                            "pz": "50",
                            "pn": str(page_num),
                            "np": "1",
                            "fltt": "2",
                            "invt": "2",
                            "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",
                            "fs": f"b:{params.sector_code}",
                            "fields": config["fields"],
                        },
                        timeout=30000,
                    )

                    if response.status == 200:
                        data = await response.json()
                        if data.get("rc") == 0:
                            all_items.extend(data.get("data", {}).get("diff", []))

                            # 如果已经获取足够数据,提前退出
                            if len(all_items) >= params.limit:
                                break

                # 解析数据
                data_list = [
                    self._parse_item(item, params.rank_type) for item in all_items[: params.limit]
                ]
                df = pd.DataFrame(data_list)

                result_data = df.to_dict(orient="records")
                if params.data_format == "markdown":
                    result_data = df.to_markdown()
                elif params.data_format == "string":
                    result_data = df.to_string()

                return SpiderResult(
                    success=True,
                    data=result_data,
                    message=f"成功获取板块 {params.sector_code} 的 {len(data_list)} 条个股数据",
                )
        except Exception as e:
            return SpiderResult(success=False, message=f"数据爬取失败:{str(e)}")

    def _parse_item(self, item: dict, rank_type: str) -> dict:
        """解析数据项"""

        def safe_float(v):
            if v in (None, "", "-"):
                return 0.0
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0

        # 基础字段
        result = {
            "股票代码": item.get("f12", ""),
            "股票名称": item.get("f14", ""),
            "最新价": safe_float(item.get("f2")),
        }

        # 根据排行类型解析不同字段
        if rank_type == "today":
            result.update(
                {
                    "涨跌幅(%)": safe_float(item.get("f3")),
                    "主力净流入(亿元)": round(safe_float(item.get("f62")) / 100000000, 2),
                    "主力净占比(%)": safe_float(item.get("f184")),
                    "超大单净流入(亿元)": round(safe_float(item.get("f66")) / 100000000, 2),
                    "超大单净占比(%)": safe_float(item.get("f69")),
                    "大单净流入(亿元)": round(safe_float(item.get("f72")) / 100000000, 2),
                    "大单净占比(%)": safe_float(item.get("f75")),
                    "中单净流入(亿元)": round(safe_float(item.get("f78")) / 100000000, 2),
                    "中单净占比(%)": safe_float(item.get("f81")),
                    "小单净流入(亿元)": round(safe_float(item.get("f84")) / 100000000, 2),
                    "小单净占比(%)": safe_float(item.get("f87")),
                }
            )
        elif rank_type == "5day":
            result.update(
                {
                    "5日涨跌幅(%)": safe_float(item.get("f109")),
                    "5日主力净流入(亿元)": round(safe_float(item.get("f164")) / 100000000, 2),
                    "5日主力净占比(%)": safe_float(item.get("f165")),
                    "5日超大单净流入(亿元)": round(safe_float(item.get("f166")) / 100000000, 2),
                    "5日超大单净占比(%)": safe_float(item.get("f167")),
                    "5日大单净流入(亿元)": round(safe_float(item.get("f168")) / 100000000, 2),
                    "5日大单净占比(%)": safe_float(item.get("f169")),
                    "5日中单净流入(亿元)": round(safe_float(item.get("f170")) / 100000000, 2),
                    "5日中单净占比(%)": safe_float(item.get("f171")),
                    "5日小单净流入(亿元)": round(safe_float(item.get("f172")) / 100000000, 2),
                    "5日小单净占比(%)": safe_float(item.get("f173")),
                }
            )
        elif rank_type == "10day":
            result.update(
                {
                    "10日涨跌幅(%)": safe_float(item.get("f160")),
                    "10日主力净流入(亿元)": round(safe_float(item.get("f174")) / 100000000, 2),
                    "10日主力净占比(%)": safe_float(item.get("f175")),
                    "10日超大单净流入(亿元)": round(safe_float(item.get("f176")) / 100000000, 2),
                    "10日超大单净占比(%)": safe_float(item.get("f177")),
                    "10日大单净流入(亿元)": round(safe_float(item.get("f178")) / 100000000, 2),
                    "10日大单净占比(%)": safe_float(item.get("f179")),
                    "10日中单净流入(亿元)": round(safe_float(item.get("f180")) / 100000000, 2),
                    "10日中单净占比(%)": safe_float(item.get("f181")),
                    "10日小单净流入(亿元)": round(safe_float(item.get("f182")) / 100000000, 2),
                    "10日小单净占比(%)": safe_float(item.get("f183")),
                }
            )

        # 更新时间(所有类型通用)
        result["更新时间"] = (
            datetime.fromtimestamp(item.get("f124", 0)).strftime("%Y-%m-%d %H:%M:%S")
            if item.get("f124")
            else ""
        )

        return result
