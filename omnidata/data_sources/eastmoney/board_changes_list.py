"""
东方财富网当日板块异动详情 Spider
获取全市场板块的当日盘口异动汇总数据

从 https://quote.eastmoney.com/changes/boardlist.html 页面获取数据
支持按异动次数、涨跌幅、主力资金流等排序，展示每个板块的当日异动总览
包括板块代码、名称、涨跌幅、主力资金流、异动总次数、最大异动股、各类型异动次数明细等

API 接口:
- 当日板块异动详情: https://push2ex.eastmoney.com/getAllBKChanges
"""

import json
import re
from typing import Literal

import pandas as pd
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney.board_changes import (
    CHANGE_TYPE_MAP,
    MARKET_MAP,
)


class BoardChangesListParams(BaseModel):
    """板块当日异动详情参数模型"""

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(
        default=100,
        ge=1,
        le=2000,
        description="每页板块数量，最大 2000（一次可拉全市场）",
    )
    sort_field: Literal["ct", "u", "zjl"] = Field(
        default="ct",
        description="排序字段：ct=异动总次数, u=涨跌幅(%), zjl=主力资金流(元)",
    )
    sort_dir: Literal["desc", "asc"] = Field(
        default="desc", description="排序方向：desc=降序, asc=升序"
    )
    min_change_count: int = Field(
        default=0, ge=0, description="过滤：仅保留异动总次数 >= 该值的板块，0 不过滤"
    )
    change_type: int | None = Field(
        default=None,
        description=(
            "过滤：仅保留包含指定异动类型（编号）的板块，None 不过滤。"
            " 可选：1/2/4/8/16/32/64/128/256/512/8193/8194/8201-8222"
        ),
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class BoardChangesListSpider(BaseWebSpider):
    """
    当日板块异动详情 Spider

    从东方财富网获取全市场板块的当日盘口异动汇总
    包括每个板块的异动总次数、涨跌幅、主力资金流、最大异动股、28 种异动类型次数明细等
    """

    name = "eastmoney_board_changes_list"
    description = (
        "获取全市场板块的当日盘口异动详情，包括每个板块的异动总次数、涨跌幅、"
        "主力资金流、最大异动股以及各类型异动次数明细（28 种）"
    )
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = BoardChangesListParams

    # API 配置
    # 页面入口：https://quote.eastmoney.com/changes/boardlist.html
    PAGE_URL = "https://quote.eastmoney.com/changes/boardlist.html"
    API_URL = "https://push2ex.eastmoney.com/getAllBKChanges"
    DEFAULT_UT = "7eea3edcaed734bea9cbfc24409ed989"

    async def crawl(self, params: BoardChangesListParams) -> SpiderResult:
        """
        爬取全市场板块的当日异动详情

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # ── 动态提取 ut 令牌：拦截页面加载时自身发起的 push2ex API 请求 ──
                captured_ut: dict[str, str] = {}

                async def capture_ut(route):
                    m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                    if m:
                        captured_ut["token"] = m.group(1)
                    await route.continue_()

                await page.route("**push2ex.eastmoney.com**", capture_ut)
                await page.goto(self.PAGE_URL)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程
                    pass

                ut = captured_ut.get("token") or self.DEFAULT_UT

                # 构建请求参数
                # 东方财富该接口的 pageindex 从 0 开始
                request_params = {
                    "ut": ut,
                    "dpt": "wzchanges",
                    "pageindex": params.page - 1,
                    "pagesize": params.page_size,
                }

                # 发送请求
                response = await page.request.get(
                    self.API_URL, params=request_params, timeout=30000
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False, message=f"请求失败，状态码：{response.status}"
                    )

                # 解析 JSONP 响应
                raw_text = await response.text()
                payload = self._parse_jsonp(raw_text)

                if payload is None:
                    return SpiderResult(
                        success=False, message="解析响应数据失败：返回内容不是合法的 JSONP"
                    )

                rc = payload.get("rc", 0)
                if rc != 0:
                    return SpiderResult(success=False, message=f"接口返回错误码：{rc}")

                data = payload.get("data") or {}
                change_items = data.get("allbk") or []
                if not change_items:
                    return SpiderResult(
                        success=False,
                        message="当日无板块异动数据",
                    )

                # 解析板块异动数据
                parsed = self._parse_board_items(change_items)

                # 过滤：按最小异动次数
                if params.min_change_count > 0:
                    parsed = [b for b in parsed if b["当日异动总次数"] >= params.min_change_count]

                # 过滤：按指定异动类型
                if params.change_type is not None:
                    change_type = params.change_type
                    change_name = CHANGE_TYPE_MAP.get(change_type, f"未知({change_type})")
                    parsed = [
                        b
                        for b in parsed
                        if any(y["异动类型编号"] == change_type for y in b["异动类型明细"])
                    ]
                else:
                    change_name = None

                # 排序
                sort_key_map = {
                    "ct": "当日异动总次数",
                    "u": "涨跌幅(%)",
                    "zjl": "主力资金流(元)",
                }
                sort_key = sort_key_map[params.sort_field]
                reverse = params.sort_dir == "desc"
                parsed.sort(
                    key=lambda x: (
                        x[sort_key] is None,
                        x[sort_key] if x[sort_key] is not None else 0,
                    ),
                    reverse=reverse,
                )

                df = pd.DataFrame(parsed)

                # 数据日期
                dt = data.get("dt", 0)
                data_date = (
                    f"{dt // 10000000000:04d}-{(dt // 100000000) % 100:02d}-{(dt // 1000000) % 100:02d}"
                    if dt
                    else ""
                )

                total_count = data.get("tc", len(parsed))

                # 构建消息
                filter_msg = ""
                if params.min_change_count > 0:
                    filter_msg += f"，异动次数>={params.min_change_count}"
                if change_name:
                    filter_msg += f"，含[{change_name}]"

                # 格式化输出
                if params.data_format == "markdown":
                    return SpiderResult(
                        success=True,
                        data=df.to_markdown(),
                        message=(
                            f"成功获取{data_date}当日板块异动详情，"
                            f"共{total_count}个板块，本页{len(parsed)}个"
                            f"{filter_msg}"
                        ),
                    )
                if params.data_format == "string":
                    return SpiderResult(
                        success=True,
                        data=df.to_string(),
                        message=(
                            f"成功获取{data_date}当日板块异动详情，"
                            f"共{total_count}个板块，本页{len(parsed)}个"
                            f"{filter_msg}"
                        ),
                    )

                # 默认返回 dict 格式
                return SpiderResult(
                    success=True,
                    data={
                        "数据日期": data_date,
                        "板块总数": total_count,
                        "当前页": params.page,
                        "每页数量": params.page_size,
                        "排序字段": params.sort_field,
                        "排序方向": params.sort_dir,
                        "过滤条件": {
                            "最小异动次数": params.min_change_count,
                            "指定异动类型": change_name,
                        },
                        "板块数量": len(parsed),
                        "板块列表": df.to_dict(orient="records"),
                    },
                    message=(
                        f"成功获取{data_date}当日板块异动详情，"
                        f"共{total_count}个板块，本页{len(parsed)}个"
                        f"{filter_msg}"
                    ),
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_jsonp(self, raw_text: str) -> dict | None:
        """
        解析 JSONP 响应文本，提取 JSON 部分

        Args:
            raw_text: 原始响应文本，形如 "jQuery({...});"

        Returns:
            解析后的字典，失败返回 None
        """
        if not raw_text:
            return None
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass

        # 尝试从 "callback({...});" 中提取
        match = re.search(r"\w+\s*\((.*)\)\s*;?\s*$", raw_text.strip(), re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    def _parse_board_items(self, items: list[dict]) -> list[dict]:
        """
        解析板块异动详情数据

        每条原始数据结构:
            {
                "c": 板块代码,
                "m": 市场代码,
                "n": 板块名称,
                "u": 涨跌幅,
                "zjl": 主力资金流,
                "ct": 当日异动总次数,
                "ms": {
                    "c": 股票代码,
                    "m": 市场代码,
                    "n": 股票名称,
                    "t": 异动类型编号
                },
                "ydl": [
                    {"t": 异动类型编号, "ct": 次数}
                ]
            }

        Args:
            items: 原始板块异动数据列表

        Returns:
            解析后的板块异动数据列表
        """
        result: list[dict] = []
        for item in items:
            board_code = item.get("c", "")
            board_name = item.get("n", "")

            # 涨跌幅
            try:
                change_pct = float(item.get("u", 0) or 0)
            except (ValueError, TypeError):
                change_pct = None

            # 主力资金流
            try:
                main_funds = float(item.get("zjl", 0) or 0)
            except (ValueError, TypeError):
                main_funds = None

            # 当日异动总次数
            try:
                total_changes = int(item.get("ct", 0) or 0)
            except (ValueError, TypeError):
                total_changes = 0

            # 最大异动股
            max_stock = item.get("ms") or {}
            max_stock_info = None
            if max_stock.get("c"):
                max_stock_info = {
                    "股票代码": max_stock.get("c", ""),
                    "市场": MARKET_MAP.get(max_stock.get("m", 0), str(max_stock.get("m", 0))),
                    "股票名称": max_stock.get("n", ""),
                    "触发异动类型": CHANGE_TYPE_MAP.get(
                        max_stock.get("t", 0), f"未知({max_stock.get('t', 0)})"
                    ),
                    "异动类型编号": max_stock.get("t", 0),
                }

            # 异动类型明细
            change_breakdown: list[dict] = []
            for y in item.get("ydl") or []:
                t = y.get("t", 0)
                ct = y.get("ct", 0)
                change_breakdown.append(
                    {
                        "异动类型编号": t,
                        "异动类型": CHANGE_TYPE_MAP.get(t, f"未知异动({t})"),
                        "次数": ct,
                    }
                )
            # 按次数降序
            change_breakdown.sort(key=lambda x: x["次数"], reverse=True)

            result.append(
                {
                    "板块代码": board_code,
                    "板块名称": board_name,
                    "涨跌幅(%)": change_pct,
                    "主力资金流(元)": main_funds,
                    "当日异动总次数": total_changes,
                    "最大异动股": max_stock_info,
                    "异动类型数量": len(change_breakdown),
                    "异动类型明细": change_breakdown,
                }
            )
        return result
