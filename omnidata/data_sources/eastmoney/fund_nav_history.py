"""
东方财富ETF基金/LOF基金历史净值 Spider
获取基金的历史净值、累计净值、日增长率等数据

API: https://api.fund.eastmoney.com/f10/lsjz
页面示例: https://fundf10.eastmoney.com/jjjz_159559.html
"""

import json
import random
import re
from typing import Literal

import pandas as pd
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


# 字段映射：东方财富API字段 → 中文标签
_FIELD_MAP = {
    "FSRQ": "净值日期",
    "DWJZ": "单位净值",
    "LJJZ": "累计净值",
    "JZZZL": "日增长率",
    "SGZT": "申购状态",
    "SHZT": "赎回状态",
    "FHFCZ": "分红送配",
}


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
    version = "2.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = FundNAVParams

    API_URL = "https://api.fund.eastmoney.com/f10/lsjz"
    REFERRER_URL = "https://fundf10.eastmoney.com/jjjz_{code}.html"
    PAGE_SIZE = 20  # 接口单页最大记录数

    @staticmethod
    def _ymd_to_date(ymd: str) -> str:
        """
        将YYYYMMDD格式转换为YYYY-MM-DD格式

        Args:
            ymd: YYYYMMDD格式日期字符串

        Returns:
            YYYY-MM-DD格式日期字符串
        """
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"

    @staticmethod
    def _make_callback() -> str:
        """
        生成 jQuery 风格 JSONP 回调函数名（接口服务端会校验格式）

        格式：jQuery + 20位数字 + _ + 13位毫秒时间戳
        """
        return f"jQuery{random.randint(10**19, 10**20 - 1)}_{int(random.random() * 10**14)}"

    @staticmethod
    def _extract_jsonp(text: str) -> dict | None:
        """
        解析 JSONP 响应：callback({...}) -> {...}

        Args:
            text: JSONP 响应字符串

        Returns:
            解析后的字典，解析失败返回 None
        """
        match = re.search(r"^[^(]+\((.*)\)\s*;?\s*$", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalize_record(item: dict) -> dict:
        """
        将API返回的原始记录映射为中文键值

        Args:
            item: API原始记录

        Returns:
            标准化后的记录
        """
        return {
            label: (item.get(key) if item.get(key) is not None else "")
            for key, label in _FIELD_MAP.items()
        }

    async def crawl(self, params: FundNAVParams) -> SpiderResult:
        """
        爬取基金历史净值数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("eastmoney") as page:
            await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

            # 先访问基金档案主页建立 referrer 与浏览器指纹
            referer = self.REFERRER_URL.format(code=params.fund_code)
            await page.goto(referer)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except PlaywrightTimeoutError:
                pass

            # 转换日期格式：YYYYMMDD -> YYYY-MM-DD
            sdate = self._ymd_to_date(params.start_date) if params.start_date else ""
            edate = self._ymd_to_date(params.end_date) if params.end_date else ""

            # ── 分页获取全量数据 ──
            # 使用 page.request 绕过浏览器 CORS 限制，同时自动携带 context cookies
            # 服务端要求 JSONP 响应（callback 包裹），构造 jQuery 风格 callback
            all_records = []
            total_count = 0
            page_index = 1

            while True:
                callback = self._make_callback()
                response = await page.request.get(
                    self.API_URL,
                    params={
                        "callback": callback,
                        "fundCode": params.fund_code,
                        "pageIndex": str(page_index),
                        "pageSize": str(self.PAGE_SIZE),
                        "startDate": sdate,
                        "endDate": edate,
                        "_": str(random.randint(10**12, 10**13 - 1)),
                    },
                    headers={"Referer": referer},
                    timeout=30000,
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False,
                        message=f"请求第{page_index}页失败，状态码：{response.status}",
                    )

                parsed = self._extract_jsonp(await response.text())
                if not parsed or parsed.get("ErrCode") != 0:
                    err_msg = parsed.get("ErrMsg") if parsed else None
                    return SpiderResult(
                        success=False,
                        message=err_msg
                        or f"请求第{page_index}页失败，可能基金代码 {params.fund_code} 不存在",
                    )

                # 首次请求时获取总数
                total_count = parsed.get("TotalCount", 0) or 0
                data = parsed.get("Data") or {}
                raw_list = data.get("LSJZList") or []

                if not raw_list and page_index == 1:
                    return SpiderResult(
                        success=False,
                        message=f"未找到基金代码 {params.fund_code} 的净值数据，请检查基金代码是否正确",
                    )

                all_records.extend(self._normalize_record(item) for item in raw_list)

                if len(all_records) >= total_count or len(raw_list) < self.PAGE_SIZE:
                    break

                page_index += 1

            # ── 构建返回数据 ──
            message = f"成功获取基金 {params.fund_code} 历史净值，共{len(all_records)}条记录"
            result_data = {
                "基金代码": params.fund_code,
                "净值条数": len(all_records),
                "净值历史": all_records,
            }

            if params.data_format == "markdown":
                df = pd.DataFrame(all_records)
                return SpiderResult(success=True, data=df.to_markdown(index=False), message=message)
            if params.data_format == "string":
                df = pd.DataFrame(all_records)
                return SpiderResult(success=True, data=df.to_string(index=False), message=message)
            if params.data_format == "csv":
                df = pd.DataFrame(all_records)
                return SpiderResult(success=True, data=df.to_csv(index=False), message=message)
            return SpiderResult(success=True, data=result_data, message=message)
