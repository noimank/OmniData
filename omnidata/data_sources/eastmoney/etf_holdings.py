"""
东方财富ETF基金持仓明细 Spider
获取ETF基金的持仓明细数据，包括持仓股票、占净值比例、持股数、持仓市值等信息

页面示例: https://fundf10.eastmoney.com/ccmx_159559.html
"""

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
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = ETFHoldingParams

    PAGE_URL = "https://fundf10.eastmoney.com/ccmx_{code}.html"
    REFERRER_URL = "https://fundf10.eastmoney.com/"

    async def crawl(self, params: ETFHoldingParams) -> SpiderResult:
        """
        爬取ETF基金持仓明细数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # 先访问基金档案主页建立 referrer，避免反爬
                await page.goto(self.REFERRER_URL)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程
                    pass

                # 导航到基金持仓页面
                page_url = self.PAGE_URL.format(code=params.fund_code)
                await page.goto(page_url)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程
                    pass

                # 等待持仓表格渲染完毕
                await page.wait_for_selector("#cctable table", state="attached", timeout=10000)

                # 如果指定了年份，切换年度下拉框并等待表格刷新
                if params.year:
                    await page.select_option("select#jjcc", params.year)
                    await page.wait_for_function(
                        """
                        () => {
                            const rows = document.querySelectorAll('#cctable table tbody tr');
                            return rows.length > 0 && rows[0].querySelector('td')?.textContent?.trim() !== '';
                        }
                        """,
                        timeout=10000,
                    )

                # 等待 JS 填充最新价/涨跌幅（页面 JS 将空 span 替换为实际数值）
                await page.wait_for_function(
                    """
                    () => {
                        const spans = document.querySelectorAll('#cctable table tbody tr td span[data-id^="dq"]');
                        if (spans.length === 0) return true;
                        return Array.from(spans).some(s => s.textContent.trim() !== '');
                    }
                    """,
                    timeout=10000,
                )

                # ── 提取首次加载时 JS 已填充的最新价/涨跌幅 ──
                initial_prices = await page.evaluate(
                    """
                    () => {
                        const rows = document.querySelectorAll('#cctable table tbody tr');
                        const prices = {};
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 9) {
                                const code = cells[1]?.textContent?.trim();
                                const price = cells[3]?.textContent?.trim();
                                const change = cells[4]?.textContent?.trim();
                                if (code && price) {
                                    prices[code] = { price, change };
                                }
                            }
                        });
                        return prices;
                    }
                    """
                )

                # 点击"显示全部持仓明细"展开完整列表
                show_all = await page.query_selector("#cctable .tfoot a")
                if show_all:
                    await show_all.click()
                    await page.wait_for_function(
                        """
                        () => {
                            const rows = document.querySelectorAll('#cctable table tbody tr');
                            return rows.length > 10;
                        }
                        """,
                        timeout=10000,
                    )

                # 获取完整的渲染后 HTML
                html_content = await page.inner_html("#cctable")

                # 解析表格
                holdings = self._parse_holdings_html(html_content)
                if not holdings:
                    return SpiderResult(
                        success=False,
                        message=f"未找到基金代码 {params.fund_code} 的持仓数据",
                    )

                # 提取基金名称
                fund_name = await page.evaluate(
                    """
                    () => {
                        const el = document.querySelector('#cctable h4.t a');
                        return el ? el.textContent.trim() : '';
                    }
                    """
                )

                # 提取可用年份
                arryear = await page.evaluate(
                    """
                    () => {
                        const opts = document.querySelectorAll('select#jjcc option');
                        return Array.from(opts).map(o => parseInt(o.value));
                    }
                    """
                )

                # 构建结构化数据
                holdings_list = [
                    {
                        "序号": h["seq"],
                        "股票代码": h["stock_code"],
                        "股票名称": h["stock_name"],
                        # 优先用首次加载时 JS 填充的价格（最新报告期才有），否则用表格中可能的值
                        "最新价": initial_prices.get(h["stock_code"], {}).get(
                            "price", h.get("latest_price", "")
                        ),
                        "涨跌幅": initial_prices.get(h["stock_code"], {}).get(
                            "change", h.get("change_pct", "")
                        ),
                        "占净值比例": h["nav_ratio"],
                        "持股数_万股": h["shares_wan"],
                        "持仓市值_万元": h["market_value_wan"],
                        "是否前十大重仓股": h["is_top10"],
                        "是否进入上市公司前十大流通股东": h["is_top_circulating_holder"],
                    }
                    for h in holdings
                ]

                result_data = {
                    "基金代码": params.fund_code,
                    "基金名称": fund_name,
                    "可用年份": arryear,
                    "持仓明细": holdings_list,
                    "持仓总数": len(holdings_list),
                }

                # 格式化输出
                message = (
                    f"成功获取 {fund_name}({params.fund_code}) 持仓明细，共{len(holdings_list)}条"
                )

                if params.data_format == "markdown":
                    df = pd.DataFrame(holdings_list)
                    return SpiderResult(
                        success=True,
                        data=df.to_markdown(index=False),
                        message=message,
                    )
                elif params.data_format == "string":
                    df = pd.DataFrame(holdings_list)
                    return SpiderResult(
                        success=True,
                        data=df.to_string(index=False),
                        message=message,
                    )
                else:
                    return SpiderResult(
                        success=True,
                        data=result_data,
                        message=message,
                    )

        except Exception as e:
            return SpiderResult(
                success=False,
                message=f"爬取失败：{str(e)}",
            )

    def _parse_holdings_html(self, html_content: str) -> list[dict[str, Any]]:
        """
        解析持仓表格 HTML，提取持仓明细

        表格存在两种格式：
        1. 最新报告期（含最新价/涨跌幅，9列）：
           序号 | 股票代码 | 股票名称 | 最新价 | 涨跌幅 | 相关资讯 | 占净值比例 | 持股数 | 持仓市值
        2. 历史报告期（不含最新价/涨跌幅，7列）：
           序号 | 股票代码 | 股票名称 | 相关资讯 | 占净值比例 | 持股数 | 持仓市值

        Args:
            html_content: 持仓表格 HTML 内容

        Returns:
            持仓明细列表
        """
        try:
            soup = BeautifulSoup(html_content, "lxml")
            table = soup.find("table")
            if not table:
                return []

            tbody = table.find("tbody")
            if not tbody:
                return []

            rows = tbody.find_all("tr")
            holdings = []

            for row in rows:
                cells = row.find_all("td")
                cell_count = len(cells)

                if cell_count < 7:
                    continue

                # 序号可能带 * 号，表示进入上市公司前十大流通股东但非基金前十大重仓股
                seq_text = cells[0].get_text(strip=True)
                has_star_mark = "*" in seq_text
                seq_num = int(seq_text.replace("*", ""))

                stock_code = cells[1].get_text(strip=True)
                stock_name = cells[2].get_text(strip=True)

                if cell_count >= 9:
                    # 9列表格：含最新价和涨跌幅（最新报告期，页面JS已填充数值）
                    latest_price = cells[3].get_text(strip=True)
                    change_pct = cells[4].get_text(strip=True)
                    # cells[5] = 相关资讯链接
                    nav_ratio = cells[6].get_text(strip=True)
                    shares_wan = cells[7].get_text(strip=True)
                    market_value_wan = cells[8].get_text(strip=True)
                else:
                    # 7列表格：不含最新价和涨跌幅（历史报告期）
                    latest_price = ""
                    change_pct = ""
                    # cells[3] = 相关资讯链接
                    nav_ratio = cells[4].get_text(strip=True)
                    shares_wan = cells[5].get_text(strip=True)
                    market_value_wan = cells[6].get_text(strip=True)

                holdings.append(
                    {
                        "seq": seq_num,
                        "is_top10": seq_num <= 10,
                        "is_top_circulating_holder": has_star_mark,
                        "stock_code": stock_code,
                        "stock_name": stock_name,
                        "latest_price": latest_price,
                        "change_pct": change_pct,
                        "nav_ratio": nav_ratio,
                        "shares_wan": shares_wan,
                        "market_value_wan": market_value_wan,
                    }
                )

            return holdings
        except Exception:
            return []
