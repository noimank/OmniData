"""
东方财富基金行业配置 Spider
获取基金（ETF/LOF/普通基金等）的行业配置数据，包括各行业类别占净值比例、市值等

页面示例: https://fundf10.eastmoney.com/hytz_159559.html
"""

from typing import Any, Literal

import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class FundIndustryAllocationParams(BaseModel):
    """基金行业配置参数模型"""

    fund_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="基金代码，6位数字，例如：159559（机器人ETF景顺）、510050（上证50ETF）",
    )
    year: str | None = Field(
        default=None,
        description="查询年份，例如：2026（最新报告期）、2025、2024、2023，不填则使用最新年份",
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json",
        description="返回数据格式，可选值：json, dict, string, markdown",
    )


class FundIndustryAllocationSpider(BaseWebSpider):
    """
    基金行业配置 Spider

    从天天基金网（东方财富旗下）获取基金的行业配置数据，
    数据来源为 #hypztable 容器内的行业配置表格。

    表格列数不固定（按列名识别，列位置可能动态增减）：
    - 序号（必有）
    - 行业类别（必有）
    - 行业变动详情（部分报告期有，含 a 链接）
    - 占净值比例（必有）
    - 市值（万元）（必有）

    支持按年份筛选：
    - 最新年份（默认）：仅展示当前报告期一张表格
    - 历史年份：展示该年度所有季度报告的对比表格，按 Q4→Q1 顺序排列
    """

    name = "eastmoney_fund_industry_allocation"
    description = (
        "获取基金（ETF/LOF/普通基金等）的行业配置数据，"
        "包括行业类别、占净值比例、市值、行业变动详情链接等信息，"
        "支持按年份筛选（最新年份仅返回当前报告期，历史年份返回该年度所有季度报告）"
    )
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = FundIndustryAllocationParams

    PAGE_URL = "https://fundf10.eastmoney.com/hytz_{code}.html"
    REFERRER_URL = "https://fundf10.eastmoney.com/"

    async def crawl(self, params: FundIndustryAllocationParams) -> SpiderResult:
        """
        爬取基金行业配置数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

                # 先访问基金档案主页建立 referrer，避免反爬
                await page.goto(
                    self.REFERRER_URL,
                    wait_until="domcontentloaded",
                    timeout=15000,
                )

                # 导航到行业配置页面
                page_url = self.PAGE_URL.format(code=params.fund_code)
                await page.goto(page_url, wait_until="domcontentloaded", timeout=20000)

                # 等待 #hypztable 容器渲染完毕
                await page.wait_for_selector(
                    "#hypztable table",
                    state="attached",
                    timeout=10000,
                )

                # 等待年份下拉框渲染完毕
                await page.wait_for_selector(
                    "select#hypz option",
                    state="attached",
                    timeout=10000,
                )

                # 提取基金名称
                fund_name = await page.evaluate(
                    """
                    () => {
                        const h4 = document.querySelector('h4');
                        if (!h4) return '';
                        // 移除子元素（如"+"号按钮）只保留文本
                        return h4.childNodes[0]?.textContent?.trim() || h4.textContent.trim();
                    }
                    """
                )

                # 提取可用年份
                arryear = await page.evaluate(
                    """
                    () => {
                        const opts = document.querySelectorAll('select#hypz option');
                        return Array.from(opts).map(o => o.value);
                    }
                    """
                )

                # 如果指定了年份，切换年度下拉框
                if params.year:
                    if params.year not in arryear:
                        return SpiderResult(
                            success=False,
                            message=f"年份 {params.year} 不可用，可用年份：{arryear}",
                        )
                    if arryear[0] != params.year:
                        await page.select_option("select#hypz", params.year)
                        # 等待下拉框值已切换
                        await page.wait_for_function(
                            """
                            (year) => {
                                const sel = document.querySelector('select#hypz');
                                return sel && sel.value === year;
                            }
                            """,
                            arg=params.year,
                            timeout=5000,
                        )
                        # 等待 #hypztable 内容重新渲染（DOM变化）
                        await page.wait_for_function(
                            """
                            () => {
                                const container = document.querySelector('#hypztable');
                                if (!container) return false;
                                const tables = container.querySelectorAll('table');
                                if (tables.length === 0) return false;
                                // 至少有一个表格带有数据行
                                return Array.from(tables).some(t =>
                                    t.querySelectorAll('tbody tr, tr').length > 1
                                );
                            }
                            """,
                            timeout=10000,
                        )

                # 获取 #hypztable 容器的完整渲染后 HTML
                html_content = await page.evaluate(
                    """
                    () => {
                        const container = document.querySelector('#hypztable');
                        return container ? container.innerHTML : '';
                    }
                    """
                )

                # 当前选中的年份
                current_year = await page.evaluate(
                    """
                    () => {
                        const sel = document.querySelector('select#hypz');
                        return sel ? sel.value : '';
                    }
                    """
                )

                # 解析表格
                report_groups = self._parse_allocation_html(html_content)
                if not report_groups:
                    return SpiderResult(
                        success=False,
                        message=f"未找到基金代码 {params.fund_code} 的行业配置数据",
                    )

                # 展平所有报告期的数据，每条记录附带报告期描述与截止日期
                allocations_list = []
                for group in report_groups:
                    for item in group["items"]:
                        allocations_list.append(
                            {
                                "报告期": group["report_label"],
                                "截止日期": group["report_date"],
                                "序号": item["seq"],
                                "行业类别": item["industry_name"],
                                "占净值比例": item["nav_ratio"],
                                "市值_万元": item["market_value_wan"],
                                # 仅最新报告期（含"行业变动详情"列）才有值
                                "行业变动详情链接": item.get("change_detail_url", ""),
                            }
                        )

                result_data = {
                    "基金代码": params.fund_code,
                    "基金名称": fund_name,
                    "当前年份": current_year,
                    "可用年份": arryear,
                    "行业配置": allocations_list,
                    "配置记录数": len(allocations_list),
                    "报告期数": len(report_groups),
                }

                # 格式化输出
                year_label = f"({current_year}年)" if current_year else ""
                if len(report_groups) == 1:
                    message = (
                        f"成功获取 {fund_name}({params.fund_code}) {year_label} 行业配置，"
                        f"共{len(allocations_list)}个行业"
                    )
                else:
                    message = (
                        f"成功获取 {fund_name}({params.fund_code}) {year_label} 行业配置，"
                        f"共{len(report_groups)}个报告期，{len(allocations_list)}条记录"
                    )

                if params.data_format == "markdown":
                    df = pd.DataFrame(allocations_list)
                    return SpiderResult(
                        success=True,
                        data=df.to_markdown(index=False),
                        message=message,
                    )
                elif params.data_format == "string":
                    df = pd.DataFrame(allocations_list)
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

    def _parse_allocation_html(self, html_content: str) -> list[dict[str, Any]]:
        """
        解析 #hypztable 容器内的所有行业配置表格

        #hypztable 内的每个 <div class="box"> 包含一张表格及配套的报告期信息：
        - <h4 class="t"> 内 <label class="left">: 报告期描述（如"2025年4季度行业配置明细"）
        - <h4 class="t"> 内 <font class="px12">: 截止日期（如"2025-12-31"）

        表格列数不固定（按列名识别，列位置可能动态增减）：
        - 序号（必有）
        - 行业类别（必有）
        - 行业变动详情（部分报告期有）
        - 占净值比例（必有）
        - 市值（万元）（必有）
        - 行业市盈率（仅最新报告期有，图片占位由 JS 动态填充）

        为应对列数变化，本方法按 th 文本映射列索引，再按索引取值。

        Args:
            html_content: #hypztable 容器的 HTML 内容

        Returns:
            报告期分组列表，每个元素包含 report_label（报告期描述）、
            report_date（截止日期 YYYY-MM-DD）与 items（行业配置明细）
        """
        try:
            soup = BeautifulSoup(html_content, "lxml")
            # 以 .box 为单位遍历（每个 .box 包含一个报告期的 h4 标题 + table）
            boxes = soup.find_all("div", class_="box")
            if not boxes:
                return []

            report_groups = []
            for box in boxes:
                table = box.find("table")
                if not table:
                    continue

                # 校验：必须是行业配置表（含"行业类别"列）
                ths = table.find_all("th")
                if not any("行业类别" in th.get_text() for th in ths):
                    continue

                # ── 建立 列名→索引 映射 ──
                # 这样无论列数怎么变（4/5/6 列），都能按列名正确定位
                header_to_index: dict[str, int] = {}
                for idx, th in enumerate(ths):
                    header_text = th.get_text(strip=True)
                    # 一个 th 可能是空 <th></th>（占位列），跳过
                    if header_text:
                        header_to_index[header_text] = idx

                def col_value(cells: list, name: str) -> str:
                    """按列名取值，找不到返回空串"""
                    if name in header_to_index:
                        i = header_to_index[name]
                        if i < len(cells):
                            return cells[i].get_text(strip=True)
                    return ""

                def col_link_href(cells: list, name: str) -> str:
                    """按列名取该列内 a 标签的 href，补全为完整 URL"""
                    if name in header_to_index:
                        i = header_to_index[name]
                        if i < len(cells):
                            a = cells[i].find("a")
                            if a:
                                href = a.get("href", "")
                                if href and not href.startswith("http"):
                                    return f"https://fundf10.eastmoney.com/{href.lstrip('/')}"
                                return href
                    return ""

                # 提取报告期信息
                h4 = box.find("h4", class_="t")
                if h4:
                    left_label = h4.find("label", class_="left")
                    date_font = h4.find("font", class_="px12")
                    # 报告期描述：去掉基金名链接和 nbsp，如 "2025年4季度行业配置明细"
                    report_label = left_label.get_text(strip=True) if left_label else ""
                    # 截止日期，如 "2025-12-31"
                    report_date = date_font.get_text(strip=True) if date_font else ""
                else:
                    report_label = ""
                    report_date = ""

                rows = table.find_all("tr")
                items = []

                for row in rows:
                    cells = row.find_all("td")
                    if not cells:
                        continue  # 跳过表头行
                    if len(cells) < 4:
                        continue  # 数据不完整，跳过

                    # 序号与行业类别永远在前两列
                    seq_text = col_value(cells, "序号")
                    if not seq_text or not seq_text.isdigit():
                        continue
                    seq = int(seq_text)
                    industry_name = col_value(cells, "行业类别")

                    # 按列名取值
                    nav_ratio = col_value(cells, "占净值比例")
                    market_value_wan = col_value(cells, "市值（万元）")
                    change_detail_url = col_link_href(cells, "行业变动详情")

                    items.append(
                        {
                            "seq": seq,
                            "industry_name": industry_name,
                            "nav_ratio": nav_ratio,
                            "market_value_wan": market_value_wan,
                            "change_detail_url": change_detail_url,
                        }
                    )

                if items:
                    report_groups.append(
                        {
                            "report_label": report_label,
                            "report_date": report_date,
                            "items": items,
                        }
                    )

            return report_groups
        except Exception:
            return []
