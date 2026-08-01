"""
东方财富ETF基金持仓明细 Spider
获取ETF基金的持仓明细数据，包括持仓股票、占净值比例、持股数、持仓市值等信息

页面示例: https://fundf10.eastmoney.com/ccmx_159559.html
"""

import json
import random
import re
from typing import Any, Literal

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class ETFHoldingParams(BaseModel):
    """ETF持仓明细参数模型"""

    fund_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="基金代码，6位数字，例如：159559（机器人ETF景顺）、510050（上证50ETF）",
    )
    year: str | None = Field(
        default=None,
        description="查询年份，例如：2026，不填则返回最新报告期数据",
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, string, markdown",
    )


class ETFHoldingSpider(BaseWebSpider):
    """
    ETF基金持仓明细 Spider

    从天天基金网（东方财富旗下）获取ETF基金的持仓明细数据，
    包括：
    - 股票代码、股票名称
    - 最新价、涨跌幅
    - 占净值比例
    - 持股数（万股）
    - 持仓市值（万元）
    - 是否为前十大重仓股 / 是否进入上市公司前十大流通股东

    数据按报告期组织，支持按年份筛选。
    """

    name = "eastmoney_etf_holdings"
    description = (
        "获取ETF基金持仓明细数据，包括持仓股票、占净值比例、持股数、持仓市值等信息，支持按年份筛选"
    )
    version = "2.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = ETFHoldingParams

    # 持仓明细接口（返回含表格 HTML + 各报告期股票代码列表）
    ARCHIVE_URL = "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
    # 行情批量接口（返回最新价/涨跌幅等实时行情）
    QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    REFERRER_URL = "https://fundf10.eastmoney.com/ccmx_{code}.html"
    ARCHIVE_FIELDS = "f2,f3,f9,f12,f13,f14"

    @staticmethod
    def _extract_archive_field(text: str, field_name: str) -> Any | None:
        """
        从 var apidata={...}; 文本中提取指定字段的值

        支持字符串字段（content）和数组字段（arryear），其他类型直接返回 None。

        Args:
            text: 原始响应文本
            field_name: 字段名（content / arryear / curyear）

        Returns:
            解析后的值；字段不存在或解析失败返回 None
        """
        # 提取数组字段
        if field_name in ("arryear",):
            match = re.search(rf"{field_name}\s*:\s*\[([^\]]*)\]", text)
            if not match:
                return None
            raw = match.group(1).strip()
            return [int(x) for x in raw.split(",") if x.strip().isdigit()]

        # 提取字符串字段（content 是 JS 字符串，UTF-8 内嵌）
        if field_name == "content":
            match = re.search(rf'{field_name}\s*:\s*"', text)
            if not match:
                return None
            i = match.end()
            j = i
            while j < len(text):
                c = text[j]
                if c == "\\" and j + 1 < len(text):
                    j += 2
                    continue
                if c == '"':
                    break
                j += 1
            return text[i:j].replace('\\"', '"').replace("\\\\", "\\").replace("\\/", "/")

        return None

    @staticmethod
    def _extract_jsonp(text: str) -> dict | None:
        """
        解析 push2.eastmoney.com 接口响应

        接口同时支持 JSON 和 JSONP 两种格式（带不带 callback 都会返回 JSON），
        因此优先尝试直接 JSON 解析，失败再尝试 JSONP 提取。
        """
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            pass
        match = re.search(r"^[^(]+\((.*)\)\s*;?\s*$", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_box(box_html: str) -> tuple[list[dict[str, Any]], list[str], str]:
        """
        解析单个报告期盒子的 HTML，提取表格行、全部股票代码、基金名称

        Args:
            box_html: 一个 boxitem 内的 HTML 片段

        Returns:
            (rows, all_secids, fund_name)
            - rows: 表格行原始数据（来自 <tbody> 中 <tr> 的 <td>）
            - all_secids: 该报告期全部持仓股票代码（含非前十大）
            - fund_name: 基金名称
        """
        soup = BeautifulSoup(box_html, "lxml")
        table = soup.find("table")
        rows: list[dict[str, Any]] = []
        if table:
            tbody = table.find("tbody")
            if tbody:
                for tr in tbody.find_all("tr"):
                    cells = tr.find_all("td")
                    if len(cells) < 7:
                        continue
                    seq_text = cells[0].get_text(strip=True)
                    has_star_mark = "*" in seq_text
                    seq_num_str = seq_text.replace("*", "")
                    if not seq_num_str.isdigit():
                        continue
                    rows.append(
                        {
                            "seq": int(seq_num_str),
                            "is_top_circulating_holder": has_star_mark,
                            "stock_code": cells[1].get_text(strip=True),
                            "stock_name": cells[2].get_text(strip=True),
                            "cells": cells,
                        }
                    )

        # 提取该报告期的全部股票代码（包括非前十大）
        secids: list[str] = []
        gpdm = soup.find("div", id="gpdmList")
        if gpdm:
            secids = [s for s in gpdm.get_text(strip=True).split(",") if s]

        # 提取基金名称
        name_el = soup.select_one("h4.t a")
        fund_name = name_el.get_text(strip=True) if name_el else ""

        return rows, secids, fund_name

    @staticmethod
    def _build_quote_map(
        raw_rows: list[dict[str, Any]], quote_data: dict[str, dict]
    ) -> list[dict[str, Any]]:
        """
        将原始行数据与行情数据合并，构造标准化的持仓明细记录

        Args:
            raw_rows: 来自 _parse_box 的原始行
            quote_data: secid -> {price, change_pct} 的行情字典

        Returns:
            标准化的持仓明细记录列表
        """
        holdings: list[dict[str, Any]] = []
        for row in raw_rows:
            cells = row["cells"]
            cell_count = len(cells)
            stock_code = row["stock_code"]
            seq_num = row["seq"]

            if cell_count >= 9:
                # 9列表格：含最新价/涨跌幅的占位列（实际值由前端 JS 通过 ulist 填充）
                # 这里 cells[3] / cells[4] 通常为空，真实值在 quote 中
                nav_ratio = cells[6].get_text(strip=True)
                shares_wan = cells[7].get_text(strip=True)
                market_value_wan = cells[8].get_text(strip=True)
            else:
                # 7列表格（历史报告期，无最新价/涨跌幅列）
                nav_ratio = cells[4].get_text(strip=True)
                shares_wan = cells[5].get_text(strip=True)
                market_value_wan = cells[6].get_text(strip=True)

            # 通过 secid 匹配最新价/涨跌幅
            secid_key = None
            for sid in (f"0.{stock_code}", f"1.{stock_code}"):
                if sid in quote_data:
                    secid_key = sid
                    break

            price = ""
            change_pct = ""
            if secid_key:
                q = quote_data[secid_key]
                f2 = q.get("f2")
                f3 = q.get("f3")
                if f2 is not None and f2 != "-":
                    price = f"{f2:.2f}"
                if f3 is not None and f3 != "-":
                    change_pct = f"{f3:.2f}%"

            holdings.append(
                {
                    "序号": seq_num,
                    "股票代码": stock_code,
                    "股票名称": row["stock_name"],
                    "最新价": price,
                    "涨跌幅": change_pct,
                    "占净值比例": nav_ratio,
                    "持股数_万股": shares_wan,
                    "持仓市值_万元": market_value_wan,
                    "是否前十大重仓股": seq_num <= 10,
                    "是否进入上市公司前十大流通股东": row["is_top_circulating_holder"],
                }
            )
        return holdings

    async def crawl(self, params: ETFHoldingParams) -> SpiderResult:
        """
        爬取ETF基金持仓明细数据

        通过两个直接 API 调用完成：
        1. FundArchivesDatas.aspx 获取持仓表格 HTML + 全部股票代码
        2. push2.eastmoney.com ulist.np/get 批量获取最新价 / 涨跌幅

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # 先访问基金档案主页建立 referrer 与浏览器指纹
                referer = self.REFERRER_URL.format(code=params.fund_code)
                await page.goto(referer)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except PlaywrightTimeoutError:
                    pass

                # 暖手：先访问 push2 域的页面，建立 push2 接口所需的 cookies
                try:
                    await page.goto("https://quote.eastmoney.com/center/gridlist.html")
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except PlaywrightTimeoutError:
                        pass
                    # 暖手后再次回到 referer
                    await page.goto(referer)
                except Exception:
                    pass

                # ── 1. 拉取持仓明细（FundArchivesDatas.aspx） ──
                archive_response = await page.context.request.get(
                    self.ARCHIVE_URL,
                    params={
                        "type": "jjcc",
                        "code": params.fund_code,
                        "topline": "200",
                        "year": params.year or "",
                        "month": "",
                        "rt": f"0.{random.randint(100000, 999999)}",
                    },
                    headers={"Referer": referer},
                    timeout=30000,
                )
                if archive_response.status != 200:
                    return SpiderResult(
                        success=False,
                        message=f"请求持仓明细失败，状态码：{archive_response.status}",
                    )

                archive_text = await archive_response.text()
                arryear = self._extract_archive_field(archive_text, "arryear") or []
                content_html = self._extract_archive_field(archive_text, "content") or ""
                if not content_html:
                    return SpiderResult(
                        success=False,
                        message=f"未找到基金代码 {params.fund_code} 的持仓数据，请检查基金代码是否正确",
                    )

                # content 是多个 boxitem 的 HTML 片段
                soup = BeautifulSoup(content_html, "lxml")
                boxes = soup.find_all("div", class_="boxitem") or [soup]
                if not boxes:
                    return SpiderResult(
                        success=False,
                        message=f"基金 {params.fund_code} 暂无持仓数据",
                    )

                # ── 2. 汇总所有 box 的 secid 用于行情批量查询 ──
                all_secids: list[str] = []
                box_infos: list[tuple[list[dict[str, Any]], list[str], str]] = []
                for box in boxes:
                    rows, secids, fund_name = self._parse_box(str(box))
                    if not rows:
                        continue
                    box_infos.append((rows, secids, fund_name))
                    for sid in secids:
                        if sid and sid not in all_secids:
                            all_secids.append(sid)

                if not box_infos:
                    return SpiderResult(
                        success=False,
                        message=f"未找到基金代码 {params.fund_code} 的持仓数据",
                    )

                # ── 3. 批量查询行情（ulist.np/get） ──
                quote_data: dict[str, dict] = {}
                if all_secids:
                    quote_response = await page.context.request.get(
                        self.QUOTE_URL,
                        params={
                            "fltt": "2",
                            "invt": "2",
                            "fields": self.ARCHIVE_FIELDS,
                            "ut": "267f9ad526dbe6b0262ab19316f5a25b",
                            "secids": ",".join(all_secids) + ",",
                            "_": str(random.randint(10**12, 10**13 - 1)),
                        },
                        headers={"Referer": referer},
                        timeout=30000,
                    )
                    if quote_response.status == 200:
                        quote_payload = self._extract_jsonp(await quote_response.text())
                        if quote_payload and quote_payload.get("rc") == 0:
                            for item in (quote_payload.get("data") or {}).get("diff") or []:
                                code = item.get("f12")
                                market = item.get("f13")
                                if code and market is not None:
                                    quote_data[f"{market}.{code}"] = item

                # ── 4. 构造按报告期组织的返回结果 ──
                # 取最近一份报告期的基金名称作为主基金名
                primary_fund_name = next((name for _, _, name in box_infos if name), "")
                reports: list[dict[str, Any]] = []
                for rows, secids, fund_name in box_infos:
                    holdings = self._build_quote_map(rows, quote_data)
                    reports.append(
                        {
                            "基金名称": fund_name or primary_fund_name,
                            "持仓明细": holdings,
                            "持仓总数": len(holdings),
                        }
                    )

                message = (
                    f"成功获取 {primary_fund_name or params.fund_code}({params.fund_code}) "
                    f"持仓明细，共{len(reports)}个报告期"
                )

                result_data: Any = {
                    "基金代码": params.fund_code,
                    "基金名称": primary_fund_name,
                    "可用年份": arryear,
                    "报告期列表": reports,
                }
                if len(reports) == 1:
                    # 单报告期时直接展开明细，便于直接消费
                    single = reports[0]
                    result_data = {
                        "基金代码": params.fund_code,
                        "基金名称": single["基金名称"],
                        "可用年份": arryear,
                        "持仓明细": single["持仓明细"],
                        "持仓总数": single["持仓总数"],
                    }
                    message = (
                        f"成功获取 {single['基金名称'] or params.fund_code}({params.fund_code}) "
                        f"持仓明细，共{single['持仓总数']}条"
                    )

                if params.data_format in ("markdown", "string"):
                    # 单报告期直接使用持仓明细；多报告期展开为长表
                    if "持仓明细" in result_data:
                        rows_for_df = result_data["持仓明细"]
                    else:
                        rows_for_df = []
                        for r in result_data.get("报告期列表", []):
                            for h in r["持仓明细"]:
                                rows_for_df.append({"报告期": r["基金名称"], **h})
                    df = pd.DataFrame(rows_for_df)
                    formatter = df.to_markdown if params.data_format == "markdown" else df.to_string
                    return SpiderResult(
                        success=True,
                        data=formatter(index=False) if not df.empty else "无数据",
                        message=message,
                    )
                return SpiderResult(success=True, data=result_data, message=message)

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")
