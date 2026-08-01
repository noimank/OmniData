"""
东方财富网行业板块资金流 Spider
获取行业板块资金流向排行数据

通过直接调用 push2.eastmoney.com JSONP 接口获取数据（参考 etf_holdings.py），
避免在浏览器 evaluate(fetch()) 中因 CORS/网络抖动偶发 Failed to fetch。
"""

import random
import re
from datetime import datetime
from typing import Literal

import pandas as pd
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney._push2_client import fetch_with_retry


class IndustrySectorFlowParams(BaseModel):
    """行业板块资金流参数模型"""

    limit: int = Field(default=128, ge=1, le=128, description="获取数据条数，最多128条")
    rank_type: Literal["today", "5day", "10day"] = Field(
        default="today", description="排行类型：today=今日排行, 5day=5日排行, 10day=10日排行"
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回格式：json, dict, markdown, string"
    )


class IndustrySectorFlowSpider(BaseWebSpider):
    """行业板块资金流 Spider"""

    name = "eastmoney_industry_sector_flow"
    description = "获取行业板块最新资金流向排行数据"
    version = "2.0.0"
    author = "noimank"
    platform = "东方财富"
    params_model = IndustrySectorFlowParams

    PAGE_URL = "https://data.eastmoney.com/bkzj/hy.html"
    API_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    DEFAULT_UT = "8dec03ba335b81bf4ebdf7b29ec27d15"

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

    async def crawl(self, params: IndustrySectorFlowParams) -> SpiderResult:
        try:
            config = self.RANK_CONFIG[params.rank_type]

            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

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

                # ── 暖手 push2 域：建立 push2 接口所需的 cookies（参考 etf_holdings.py） ──
                try:
                    await page.goto("https://quote.eastmoney.com/center/gridlist.html")
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except PlaywrightTimeoutError:
                        pass
                    await page.goto(self.PAGE_URL)
                except Exception:
                    pass

                base_api_params = {
                    "fid": config["fid"],
                    "po": "1",
                    "pz": "50",
                    "pn": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "ut": ut,
                    "fs": "m:90+s:4",
                    "fields": config["fields"],
                    "_": str(random.randint(10**12, 10**13 - 1)),
                }

                all_items: list[dict] = []
                page_num = 1

                while True:
                    api_params = {**base_api_params, "pn": str(page_num)}
                    result = await fetch_with_retry(
                        page, self.API_URL, api_params, referer=self.PAGE_URL, response_type="json"
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
                    if page_num > 3 or len(all_items) >= params.limit:
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
                    success=True, data=result_data, message=f"成功获取 {len(data_list)} 条数据"
                )
        except Exception as e:
            return SpiderResult(success=False, message=f"数据爬取失败：{str(e)}")

    def _parse_item(self, item: dict, rank_type: str) -> dict:
        """解析数据项"""

        def safe_float(v):
            return float(v) if v not in (None, "") else 0.0

        # 基础字段
        result = {
            "板块代码": item.get("f12", ""),
            "板块名称": item.get("f14", ""),
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
                    "领涨股票": item.get("f204", ""),
                    "领涨股票代码": item.get("f205", ""),
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
                    "领涨股票": item.get("f257", ""),
                    "领涨股票代码": item.get("f258", ""),
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
                    "领涨股票": item.get("f260", ""),
                    "领涨股票代码": item.get("f261", ""),
                }
            )

        # 更新时间（所有类型通用）
        result["更新时间"] = (
            datetime.fromtimestamp(item.get("f124", 0)).strftime("%Y-%m-%d %H:%M:%S")
            if item.get("f124")
            else ""
        )

        return result
