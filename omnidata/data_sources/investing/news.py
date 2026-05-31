"""
英为财情 (Investing.com) 新闻 Spider
通过 RSS 订阅源获取全球市场新闻

支持的新闻类别：全部（并发合并）、股票市场、加密货币、大宗商品、外汇、经济、公司新闻
"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult

# RSS 订阅源 ID 映射（已验证全部返回实时数据）
CATEGORY_MAP = {
    "stock_market": "news_25",
    "crypto": "news_301",
    "commodities": "news_11",
    "forex": "news_1",
    "economy": "news_14",
    "company": "news_95",
}

CATEGORY_LABELS = {
    "all": "全部新闻",
    "stock_market": "股票市场",
    "crypto": "加密货币",
    "commodities": "大宗商品",
    "forex": "外汇",
    "economy": "经济",
    "company": "公司新闻",
}


class InvestingNewsParams(BaseModel):
    category: str = Field(
        default="all",
        description=(
            "新闻类别: "
            + ", ".join(f"{k}({v})" for k, v in CATEGORY_LABELS.items())
        ),
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=50,
        description="获取新闻数量，默认20条，最大50条",
    )


class InvestingNewsSpider(BaseWebSpider):
    """
    英为财情新闻 Spider

    通过 Investing.com 官方 RSS 订阅源获取全球财经新闻
    all 类别并发抓取所有分类后按时间倒序合并
    """

    name = "investing_news"
    description = "获取英为财情全球财经新闻，支持多类别筛选"
    version = "1.0.0"
    author = "noimank"
    platform = "英为财情"

    params_model = InvestingNewsParams

    RSS_BASE_URL = "https://www.investing.com/rss/{}.rss"

    async def crawl(self, params: InvestingNewsParams) -> SpiderResult:
        valid_categories = list(CATEGORY_MAP.keys()) + ["all"]
        if params.category not in valid_categories:
            return SpiderResult(
                success=False,
                message=f"不支持的类别 '{params.category}'，可选值：{', '.join(valid_categories)}",
            )

        try:
            if params.category == "all":
                return await self._crawl_all(params.limit)
            return await self._crawl_single(params.category, params.limit)
        except ET.ParseError as e:
            return SpiderResult(success=False, message=f"RSS 解析失败：{str(e)}")
        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    async def _crawl_single(self, category: str, limit: int) -> SpiderResult:
        feed_id = CATEGORY_MAP[category]
        feed_url = self.RSS_BASE_URL.format(feed_id)

        async with self.new_page("investing") as page:
            response = await page.request.get(feed_url, timeout=30000)

            if response.status != 200:
                return SpiderResult(
                    success=False,
                    message=f"请求失败，状态码：{response.status}",
                )

            xml_text = await response.text()

        items = self._parse_rss(xml_text)
        news_list = [self._enrich_item(item, category) for item in items[:limit]]

        return SpiderResult(
            success=True,
            data={
                "total": len(news_list),
                "category": category,
                "category_label": CATEGORY_LABELS[category],
                "news_list": news_list,
            },
            message=f"成功获取 {len(news_list)} 条{CATEGORY_LABELS[category]}新闻",
        )

    async def _crawl_all(self, limit: int) -> SpiderResult:
        async with self.new_page("investing") as page:
            tasks = [
                self._fetch_feed(page, cat, feed_id)
                for cat, feed_id in CATEGORY_MAP.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            all_news.extend(result)

        all_news.sort(key=lambda x: x.get("_sort_time", ""), reverse=True)

        news_list = all_news[:limit]
        for item in news_list:
            item.pop("_sort_time", None)

        return SpiderResult(
            success=True,
            data={
                "total": len(news_list),
                "category": "all",
                "category_label": CATEGORY_LABELS["all"],
                "news_list": news_list,
            },
            message=f"成功获取 {len(news_list)} 条全部新闻（合并自 {len(CATEGORY_MAP)} 个分类）",
        )

    async def _fetch_feed(
        self, page: Any, category: str, feed_id: str
    ) -> list[dict[str, Any]]:
        feed_url = self.RSS_BASE_URL.format(feed_id)
        response = await page.request.get(feed_url, timeout=30000)

        if response.status != 200:
            return []

        xml_text = await response.text()
        items = self._parse_rss(xml_text)
        return [self._enrich_item(item, category) for item in items]

    def _parse_rss(self, xml_text: str) -> list[dict[str, Any]]:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return []

        items = channel.findall("item")
        return [self._parse_item(item) for item in items]

    def _parse_item(self, item: ET.Element) -> dict[str, Any]:
        title = (item.findtext("title") or "").strip()
        pub_time = (item.findtext("pubDate") or "").strip()
        source = (item.findtext("author") or "").strip()
        url = (item.findtext("link") or "").strip()

        enclosure = item.find("enclosure")
        image = ""
        if enclosure is not None:
            image = enclosure.get("url", "")

        result = {
            "title": title,
            "pub_time": pub_time,
            "source": source,
            "url": url,
        }
        # if image:
        #     result["image"] = image

        return result

    def _enrich_item(self, item: dict[str, Any], category: str) -> dict[str, Any]:
        item["category"] = category
        item["category_label"] = CATEGORY_LABELS[category]
        item["_sort_time"] = item.get("pub_time", "")
        return item
