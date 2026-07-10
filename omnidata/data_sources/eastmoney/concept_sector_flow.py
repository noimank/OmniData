"""
东方财富网概念板块资金流 Spider
获取概念板块资金流向排行数据，支持今日、5日、10日排行
"""

import random
import re
from datetime import datetime
from typing import Literal

import pandas as pd
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class ConceptSectorFlowParams(BaseModel):
    """概念板块资金流参数模型"""

    limit: int = Field(default=100, ge=1, le=500, description="获取数据条数，最多500条")
    rank_type: Literal["今日", "5日", "10日"] = Field(
        default="今日", description="排行类型：今日、5日、10日"
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回格式：json, dict, markdown, string"
    )


class ConceptSectorFlowSpider(BaseWebSpider):
    """概念板块资金流 Spider"""

    name = "eastmoney_concept_sector_flow"
    description = "获取概念板块资金流向排行数据，支持今日、5日、10日排行查询"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"
    params_model = ConceptSectorFlowParams

    PAGE_URL = "https://data.eastmoney.com/bkzj/hy.html"
    API_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    DEFAULT_UT = "8dec03ba335b81bf4ebdf7b29ec27d15"

    RANK_TYPE_CONFIG = {
        "今日": {
            "fid": "f62",
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13",
        },
        "5日": {
            "fid": "f164",
            "fields": "f12,f14,f2,f109,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f257,f258,f124,f1,f13",
        },
        "10日": {
            "fid": "f174",
            "fields": "f12,f14,f2,f160,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f260,f261,f124,f1,f13",
        },
    }

    async def crawl(self, params: ConceptSectorFlowParams) -> SpiderResult:
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # ── 动态提取 ut 令牌：拦截页面加载时自身发起的 push2 API 请求 ──
                captured_ut = {}

                async def capture_ut(route):
                    m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                    if m:
                        captured_ut["token"] = m.group(1)
                    await route.continue_()

                await page.route("**push2.eastmoney.com**", capture_ut)

                await page.goto(self.PAGE_URL)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程
                    pass

                ut = captured_ut.get("token") or self.DEFAULT_UT

                config = self.RANK_TYPE_CONFIG[params.rank_type]
                api_params = {
                    "fid": config["fid"],
                    "po": "1",
                    "pz": "50",
                    "pn": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "ut": ut,
                    "fs": "m:90+t:3",
                    "fields": config["fields"],
                }

                all_items = []
                page_num = 1

                while True:
                    result = await page.evaluate(
                        """
                        async ([apiUrl, params]) => {
                            const url = new URL(apiUrl);
                            Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
                            const resp = await fetch(url.toString(), { credentials: 'include' });
                            if (!resp.ok) return null;
                            return await resp.json();
                        }
                        """,
                        [self.API_URL, api_params],
                    )

                    if result is None or result.get("rc") != 0:
                        break

                    diff = result.get("data", {}).get("diff", [])
                    if not diff:
                        break

                    all_items.extend(diff)
                    if len(diff) < 50:
                        break

                    page_num += 1
                    api_params["pn"] = str(page_num)

                    if len(all_items) >= params.limit:
                        break

                    await page.wait_for_timeout(random.randint(500, 1500))

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
                    message=f"成功获取 {params.rank_type} 排行 {len(data_list)} 条数据",
                )

        except Exception as e:
            return SpiderResult(success=False, message=str(e))

    def _parse_item(self, item: dict, rank_type: str) -> dict:
        def safe_float(v):
            return float(v) if v not in (None, "", "-") else 0.0

        result = {
            "板块代码": item.get("f12", ""),
            "板块名称": item.get("f14", ""),
            "最新价": safe_float(item.get("f2")),
        }

        if rank_type == "今日":
            result["今日涨跌幅(%)"] = safe_float(item.get("f3"))
            result["今日主力净流入(亿元)"] = round(safe_float(item.get("f62")) / 100000000, 2)
            result["今日主力净占比(%)"] = safe_float(item.get("f184"))
            result["今日超大单净流入(亿元)"] = round(safe_float(item.get("f66")) / 100000000, 2)
            result["今日超大单净占比(%)"] = safe_float(item.get("f69"))
            result["今日大单净流入(亿元)"] = round(safe_float(item.get("f72")) / 100000000, 2)
            result["今日大单净占比(%)"] = safe_float(item.get("f75"))
            result["今日中单净流入(亿元)"] = round(safe_float(item.get("f78")) / 100000000, 2)
            result["今日中单净占比(%)"] = safe_float(item.get("f81"))
            result["今日小单净流入(亿元)"] = round(safe_float(item.get("f84")) / 100000000, 2)
            result["今日小单净占比(%)"] = safe_float(item.get("f87"))
            result["今日领涨股票"] = item.get("f204", "")
            result["今日领涨股票代码"] = item.get("f205", "")

        elif rank_type == "5日":
            result["5日涨跌幅(%)"] = item.get("f109", "")
            result["5日主力净流入(亿元)"] = round(safe_float(item.get("f164")) / 100000000, 2)
            result["5日主力净流入净占比(%)"] = item.get("f165", "")
            result["5日超大单净流入(亿元)"] = round(safe_float(item.get("f166")) / 100000000, 2)
            result["5日超大单净流入净占比(%)"] = item.get("f167", "")
            result["5日大单净流入(亿元)"] = round(safe_float(item.get("f168")) / 100000000, 2)
            result["5日大单净流入净占比(%)"] = item.get("f169", "")
            result["5日中单净流入(亿元)"] = round(safe_float(item.get("f170")) / 100000000, 2)
            result["5日中单净流入净占比(%)"] = item.get("f171", "")
            result["5日小单净流入(亿元)"] = round(safe_float(item.get("f172")) / 100000000, 2)
            result["5日小单净流入净占比(%)"] = item.get("f173", "")
            result["5日领涨股票"] = item.get("f257", "")
            result["5日领涨股票代码"] = item.get("f258", "")

        else:  # 10日
            result["10日涨跌幅(%)"] = item.get("f160", "")
            result["10日主力净流入(亿元)"] = round(safe_float(item.get("f174")) / 100000000, 2)
            result["10日主力净流入净占比(%)"] = item.get("f175", "")
            result["10日超大单净流入(亿元)"] = round(safe_float(item.get("f176")) / 100000000, 2)
            result["10日超大单净流入净占比(%)"] = item.get("f177", "")
            result["10日大单净流入(亿元)"] = round(safe_float(item.get("f178")) / 100000000, 2)
            result["10日大单净流入净占比(%)"] = item.get("f179", "")
            result["10日中单净流入(亿元)"] = round(safe_float(item.get("f180")) / 100000000, 2)
            result["10日中单净流入净占比(%)"] = item.get("f181", "")
            result["10日小单净流入(亿元)"] = round(safe_float(item.get("f182")) / 100000000, 2)
            result["10日小单净流入净占比(%)"] = item.get("f183", "")
            result["10日领涨股票"] = item.get("f260", "")
            result["10日领涨股票代码"] = item.get("f261", "")

        result["更新时间"] = (
            datetime.fromtimestamp(item.get("f124", 0)).strftime("%Y-%m-%d %H:%M:%S")
            if item.get("f124")
            else ""
        )

        return result
