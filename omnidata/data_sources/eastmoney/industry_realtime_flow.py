"""
东方财富网行业实时资金流 Spider
获取指定行业板块的实时资金流向数据（分钟级）

数据说明：
- 主力资金 = 超大单 + 大单
- 超大单：单笔成交额 >= 50万元
- 大单：20万元 <= 单笔成交额 < 50万元
- 中单：5万元 <= 单笔成交额 < 20万元
- 小单：单笔成交额 < 5万元

API 来源：https://push2.eastmoney.com/api/qt/stock/fflow/kline/get
"""

import random
import re
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class IndustryRealtimeFlowParams(BaseModel):
    """行业实时资金流参数模型"""

    sector_code: str = Field(
        ...,
        description="行业板块代码，如：BK0737（软件开发）、BK0420（航空机场）",
        examples=["BK0737", "BK0420"],
    )
    limit: int = Field(
        default=0,
        ge=0,
        le=240,
        description="限制返回数据条数，0表示全部数据，最多240条数据",
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回格式：json, dict, markdown, string"
    )


class IndustryRealtimeFlowSpider(BaseWebSpider):
    """行业实时资金流 Spider"""

    name = "eastmoney_industry_realtime_flow"
    description = "获取指定行业板块的实时资金流向数据（分钟级）"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"
    params_model = IndustryRealtimeFlowParams

    PAGE_URL = "https://data.eastmoney.com/bkzj/BK0737.html"
    API_URL = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    DEFAULT_UT = "b2884a393a59ad64002292a3e90d46a5"

    async def crawl(self, params: IndustryRealtimeFlowParams) -> SpiderResult:
        try:
            # 构建完整的 secid（市场代码90 + 板块代码）
            secid = f"90.{params.sector_code}"

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
                await page.wait_for_load_state("domcontentloaded", timeout=10000)

                ut = captured_ut.get("token") or self.DEFAULT_UT

                # 请求实时资金流数据（klt=1表示分钟级）
                api_params = {
                    "lmt": str(params.limit),
                    "klt": "1",  # 1=分钟级实时数据
                    "fields1": "f1,f2,f3,f7",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
                    "ut": ut,
                    "secid": secid,
                }

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

                if result is None:
                    return SpiderResult(success=False, message="API请求失败")

                data = result

                if data.get("rc") != 0:
                    return SpiderResult(
                        success=False, message=f"API返回错误：{data.get('message', '未知错误')}"
                    )

                # 解析数据
                result_data = data.get("data", {})
                klines = result_data.get("klines", [])

                if not klines:
                    return SpiderResult(success=True, data=[], message="未获取到实时数据")

                # 解析K线数据
                data_list = [self._parse_kline(kline) for kline in klines]
                df = pd.DataFrame(data_list)

                # 添加板块信息
                metadata = {
                    "板块代码": result_data.get("code", ""),
                    "板块名称": result_data.get("name", ""),
                    "市场代码": result_data.get("market", ""),
                    "数据类型": "分钟级实时数据",
                    "数据条数": len(data_list),
                }

                result_output = df.to_dict(orient="records")
                if params.data_format == "markdown":
                    result_output = df.to_markdown()
                elif params.data_format == "string":
                    result_output = df.to_string()

                return SpiderResult(
                    success=True,
                    data={"metadata": metadata, "klines": result_output},
                    message=f"成功获取 {len(data_list)} 条实时数据",
                )
        except Exception as e:
            return SpiderResult(success=False, message=f"数据爬取失败：{str(e)}")

    def _parse_kline(self, kline: str) -> dict:
        """解析K线数据字符串

        K线数据格式（逗号分隔，共6个字段）：
        0: 时间（格式：2026-03-06 09:31）
        1: 主力净流入
        2: 小单净流入
        3: 中单净流入
        4: 大单净流入
        5: 超大单净流入

        注意：主力净流入 = 超大单净流入 + 大单净流入
        """
        fields = kline.split(",")

        def safe_float(v):
            try:
                return float(v) if v not in (None, "") else 0.0
            except (ValueError, TypeError):
                return 0.0

        return {
            "时间": fields[0] if len(fields) > 0 else "",
            "主力净流入(万)": (round(safe_float(fields[1]) / 10000, 2) if len(fields) > 1 else 0.0),
            "超大单净流入(万)": (
                round(safe_float(fields[5]) / 10000, 2) if len(fields) > 5 else 0.0
            ),
            "大单净流入(万)": (round(safe_float(fields[4]) / 10000, 2) if len(fields) > 4 else 0.0),
            "中单净流入(万)": (round(safe_float(fields[3]) / 10000, 2) if len(fields) > 3 else 0.0),
            "小单净流入(万)": (round(safe_float(fields[2]) / 10000, 2) if len(fields) > 2 else 0.0),
        }
