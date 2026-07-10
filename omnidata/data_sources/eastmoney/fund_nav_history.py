"""
东方财富ETF基金/LOF基金历史净值 Spider
获取基金的历史净值、累计净值、日增长率等数据

API: https://fundf10.eastmoney.com/F10DataApi.aspx?type=lsjz
页面示例: https://fundf10.eastmoney.com/jjjz_159559.html
"""

from typing import Literal

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class FundNAVParams(BaseModel):
    """基金历史净值参数模型"""

    fund_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="基金代码，6位数字，例如：159559（机器人ETF景顺）、510050（上证50ETF）、510300（沪深300ETF）",
    )
    start_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description="开始日期，格式：yyyyMMdd，例如：20260101，不填则从成立日开始",
    )
    end_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description="结束日期，格式：yyyyMMdd，例如：20260607，不填则到最新净值日",
    )
    data_format: Literal["json", "dict", "csv", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, csv, string, markdown",
    )


class FundNAVHistorySpider(BaseWebSpider):
    """
    ETF基金/LOF基金历史净值 Spider

    从天天基金网（东方财富旗下）获取基金的历史净值数据，
    包括：
    - 净值日期
    - 单位净值
    - 累计净值
    - 日增长率
    - 申购状态
    - 赎回状态
    - 分红送配

    支持按日期范围筛选，自动分页获取全量数据。
    """

    name = "eastmoney_fund_nav_history"
    description = "获取ETF/LOF基金历史净值数据，包括单位净值、累计净值、日增长率、申赎状态、分红送配等信息，支持日期范围筛选"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = FundNAVParams

    API_URL = "https://fundf10.eastmoney.com/F10DataApi.aspx"
    REFERRER_URL = "https://fundf10.eastmoney.com/"

    # 每页记录数（API上限20条）
    PAGE_SIZE = 20

    @staticmethod
    def _parse_nav_html(html_content: str) -> list[dict]:
        """
        解析净值历史HTML表格

        表格列（7列）：
        净值日期 | 单位净值 | 累计净值 | 日增长率 | 申购状态 | 赎回状态 | 分红送配

        Args:
            html_content: HTML表格字符串

        Returns:
            净值记录列表
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
            records = []

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue

                records.append(
                    {
                        "净值日期": cells[0].get_text(strip=True),
                        "单位净值": cells[1].get_text(strip=True),
                        "累计净值": cells[2].get_text(strip=True),
                        "日增长率": cells[3].get_text(strip=True),
                        "申购状态": cells[4].get_text(strip=True),
                        "赎回状态": cells[5].get_text(strip=True),
                        "分红送配": cells[6].get_text(strip=True),
                    }
                )

            return records
        except Exception:
            return []

    @staticmethod
    def _ymd_to_date(ymd: str) -> str:
        """
        将YYYYMMDD格式转换为YYYY-MM-DD格式

        Args:
            ymd: YYYYMMDD格式日期字符串

        Returns:
            YYYY-MM-DD格式日期字符串
        """
        if not ymd or len(ymd) != 8:
            return ""
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"

    async def crawl(self, params: FundNAVParams) -> SpiderResult:
        """
        爬取基金历史净值数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # 先访问基金档案主页建立 referrer
                await page.goto(self.REFERRER_URL)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except PlaywrightTimeoutError:
                    # DOMContentLoaded 超时不影响后续流程
                    pass

                # 转换日期格式
                sdate = self._ymd_to_date(params.start_date) if params.start_date else ""
                edate = self._ymd_to_date(params.end_date) if params.end_date else ""

                # ── 分页获取全量数据 ──
                all_records = []
                page_index = 1

                while True:
                    # 构建请求参数
                    request_params = {
                        "type": "lsjz",
                        "code": params.fund_code,
                        "page": str(page_index),
                        "per": str(self.PAGE_SIZE),
                    }
                    if sdate:
                        request_params["sdate"] = sdate
                    if edate:
                        request_params["edate"] = edate

                    # 使用浏览器 fetch 请求，带浏览器上下文（cookie/referer），绕过反爬
                    # 响应是JavaScript字面量(非合法JSON)，直接在浏览器中eval得到apidata对象
                    api_data = await page.evaluate(
                        """
                        async ([apiUrl, params]) => {
                            const url = new URL(apiUrl);
                            Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
                            const resp = await fetch(url.toString(), { credentials: 'include' });
                            if (!resp.ok) return null;
                            const text = await resp.text();
                            // 执行JavaScript文本得到apidata对象
                            const fn = new Function('var apidata; ' + text + '; return apidata;');
                            return fn();
                        }
                        """,
                        [self.API_URL, request_params],
                    )

                    if api_data is None:
                        return SpiderResult(
                            success=False,
                            message=f"请求第{page_index}页失败，可能基金代码 {params.fund_code} 不存在",
                        )

                    # 解析HTML表格
                    html_content = api_data.get("content", "")
                    records = self._parse_nav_html(html_content)

                    if not records and page_index == 1:
                        return SpiderResult(
                            success=False,
                            message=f"未找到基金代码 {params.fund_code} 的净值数据，请检查基金代码是否正确",
                        )

                    all_records.extend(records)

                    # 判断是否还有下一页
                    total_pages = api_data.get("pages", 1)
                    total_records = api_data.get("records", 0)

                    if page_index >= total_pages:
                        break

                    page_index += 1

                # ── 构建返回数据 ──
                # 按净值日期降序排列（最新在前，与页面展示顺序一致）
                result_data = {
                    "基金代码": params.fund_code,
                    "净值条数": len(all_records),
                    "净值历史": all_records,
                }

                message = f"成功获取基金 {params.fund_code} 历史净值，共{len(all_records)}条记录"

                # 格式化输出
                if params.data_format == "markdown":
                    df = pd.DataFrame(all_records)
                    return SpiderResult(
                        success=True,
                        data=df.to_markdown(index=False),
                        message=message,
                    )
                elif params.data_format == "string":
                    df = pd.DataFrame(all_records)
                    return SpiderResult(
                        success=True,
                        data=df.to_string(index=False),
                        message=message,
                    )
                elif params.data_format == "csv":
                    df = pd.DataFrame(all_records)
                    return SpiderResult(
                        success=True,
                        data=df.to_csv(index=False),
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
