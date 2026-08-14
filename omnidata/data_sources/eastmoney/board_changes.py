"""
东方财富网板块当日异动 Spider
获取指定板块的当日盘口异动数据

从 https://quote.eastmoney.com/changes/boards/{BOARD_CODE}.html 页面获取数据
支持查询任意板块（融资融券 BK0596、行业板块、概念板块等）的当日异动数据
包括每种异动类型的次数、相关个股及涨跌幅等

API 接口:
- 当日异动: https://push2ex.eastmoney.com/getBKChanges
- 历史异动: https://push2ex.eastmoney.com/getBKHistoryChanges
"""

import json
import re
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult

# 板块异动类型编号 -> 中文名称
# 来源: changes_board.js (https://quote.eastmoney.com/newstatic/build/changes_board.js)
CHANGE_TYPE_MAP: dict[int, str] = {
    1: "顶级买单",
    2: "顶级卖单",
    4: "封涨停板",
    8: "封跌停板",
    16: "打开涨停板",
    32: "打开跌停板",
    64: "有大买盘",
    128: "有大卖盘",
    256: "机构买单",
    512: "机构卖单",
    8193: "大笔买入",
    8194: "大笔卖出",
    8195: "拖拉机买",
    8196: "拖拉机卖",
    8201: "火箭发射",
    8202: "快速反弹",
    8203: "高台跳水",
    8204: "加速下跌",
    8205: "买入撤单",
    8206: "卖出撤单",
    8207: "竞价上涨",
    8208: "竞价下跌",
    8209: "高开5日线",
    8210: "低开5日线",
    8211: "向上缺口",
    8212: "向下缺口",
    8213: "60日新高",
    8214: "60日新低",
    8215: "60日大幅上涨",
    8216: "60日大幅下跌",
    8217: "向上跳空",
    8218: "向下跳空",
    8219: "放量上涨",
    8220: "放量下跌",
    8221: "缩量上涨",
    8222: "缩量下跌",
}

# 市场代码 -> 中文名称
MARKET_MAP: dict[int, str] = {
    0: "深市",
    1: "沪市",
    2: "北证",
}


class BoardChangesParams(BaseModel):
    """板块当日异动参数模型"""

    board_code: str = Field(
        default="BK0596",
        description="板块代码，如 BK0596(融资融券)、BK0420(航空机场)、BK0475(银行Ⅱ) 等",
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class BoardChangesSpider(BaseWebSpider):
    """
    板块当日异动 Spider

    从东方财富网获取指定板块的当日盘口异动数据
    包括每种异动类型的次数（当日/近期）、最频繁异动个股、相关个股列表等
    """

    name = "eastmoney_board_changes"
    description = (
        "获取指定板块的当日盘口异动数据，包括各种异动类型（涨停板/火箭发射/大笔买卖等）的次数和个股"
    )
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = BoardChangesParams

    # API 配置
    API_URL = "https://push2ex.eastmoney.com/getBKChanges"
    UT = "7eea3edcaed734bea9cbfc24409ed989"

    async def crawl(self, params: BoardChangesParams) -> SpiderResult:
        """
        爬取板块当日异动数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("eastmoney") as page:
            await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])
            await page.goto("https://quote.eastmoney.com/")

            # 构建请求参数
            request_params = {
                "ut": self.UT,
                "dpt": "wzchanges",
                "bk": params.board_code,
            }

            # 发送请求
            response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

            if response.status != 200:
                return SpiderResult(success=False, message=f"请求失败，状态码：{response.status}")

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
            change_items = data.get("data") or []
            if not change_items:
                return SpiderResult(
                    success=False,
                    message=f"板块 {params.board_code} 当日无异动数据",
                )

            # 解析异动数据
            parsed = self._parse_change_items(change_items)

            df = pd.DataFrame(parsed)

            # 统计当日总览
            board_name = data.get("n", params.board_code)
            dt = data.get("dt", 0)  # 数据时间戳 YYYYMMDDhhmmss
            data_date = (
                f"{dt // 10000000000:04d}-{(dt // 100000000) % 100:02d}-{(dt // 1000000) % 100:02d}"
                if dt
                else ""
            )

            # 格式化输出
            if params.data_format == "markdown":
                return SpiderResult(
                    success=True,
                    data=df.to_markdown(),
                    message=(
                        f"成功获取{board_name}({params.board_code})"
                        f"{data_date}当日盘口异动数据，共{len(parsed)}种异动类型"
                    ),
                )
            if params.data_format == "string":
                return SpiderResult(
                    success=True,
                    data=df.to_string(),
                    message=(
                        f"成功获取{board_name}({params.board_code})"
                        f"{data_date}当日盘口异动数据，共{len(parsed)}种异动类型"
                    ),
                )

            # 默认返回 dict 格式
            return SpiderResult(
                success=True,
                data={
                    "板块代码": params.board_code,
                    "板块名称": board_name,
                    "数据日期": data_date,
                    "异动类型数量": len(parsed),
                    "异动列表": df.to_dict(orient="records"),
                },
                message=(
                    f"成功获取{board_name}({params.board_code})"
                    f"{data_date}当日盘口异动数据，共{len(parsed)}种异动类型"
                ),
            )

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

    def _parse_change_items(self, items: list[dict]) -> list[dict]:
        """
        解析异动数据列表

        每条原始数据结构:
            {
                "t": 异动类型编号(int),
                "2c": [近期次数, 当日次数] (推测/部分接口字段),
                "2s": [
                    {"c": "股票代码", "m": 市场代码, "u": "涨跌幅", "ct": 次数}
                ],  # 最频繁异动个股（通常 1-2 个）
                "as": [
                    {"c": "股票代码", "m": 市场代码, "ct": 次数, "u": "涨跌幅"}
                ]   # 异动个股列表（多只）
            }

        Args:
            items: 原始异动数据列表

        Returns:
            解析后的异动数据列表
        """
        result: list[dict] = []
        for item in items:
            change_type = item.get("t")
            change_name = CHANGE_TYPE_MAP.get(change_type, f"未知异动({change_type})")

            # 2c 字段：[近期总次数, 当日次数] - 异动次数详情
            count_pair = item.get("2c") or []
            recent_count = count_pair[0] if len(count_pair) >= 1 else None
            today_count = count_pair[1] if len(count_pair) >= 2 else None

            # 最频繁异动个股（2s 字段）
            top_stocks: list[dict] = []
            for stock in item.get("2s") or []:
                code = stock.get("c", "")
                market_code = stock.get("m", 0)
                change_pct_raw = stock.get("u", "")
                try:
                    change_pct = float(change_pct_raw) if change_pct_raw not in (None, "") else None
                except (ValueError, TypeError):
                    change_pct = None
                top_stocks.append(
                    {
                        "股票代码": code,
                        "市场": MARKET_MAP.get(market_code, str(market_code)),
                        "涨跌幅(%)": change_pct,
                    }
                )

            # 相关个股列表（as 字段）
            related_stocks: list[dict] = []
            for stock in item.get("as") or []:
                code = stock.get("c", "")
                market_code = stock.get("m", 0)
                stock_today_count = stock.get("ct", 0)
                change_pct_raw = stock.get("u", "")
                try:
                    change_pct = float(change_pct_raw) if change_pct_raw not in (None, "") else None
                except (ValueError, TypeError):
                    change_pct = None
                related_stocks.append(
                    {
                        "股票代码": code,
                        "市场": MARKET_MAP.get(market_code, str(market_code)),
                        "涨跌幅(%)": change_pct,
                        "当日异动次数": stock_today_count,
                    }
                )

            result.append(
                {
                    "异动类型编号": change_type,
                    "异动类型": change_name,
                    "近期累计次数": recent_count,
                    "当日次数": today_count,
                    "最频繁异动个股": top_stocks,
                    "相关个股数": len(related_stocks),
                    "相关个股": related_stocks,
                }
            )
        return result
