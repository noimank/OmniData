"""
市场观察（MarketWatch）新闻快讯 Spider

聚合 MarketWatch 四个官方 RSS feed，按发布时间倒序取最新新闻快讯

接口说明：
MarketWatch 官网（www.marketwatch.com）受 DataDome 反爬保护（裸 HTTP 客户端返回验证页），
但官方 RSS 快讯接口部署在独立域名 feeds.content.dowjones.io 上，完全公开、无需鉴权。
聚合四个 feed：
  - mw_topstories            Top Stories 头条（唯一带摘要的 feed）
  - mw_realtimeheadlines     实时标题
  - mw_marketpulse           Market Pulse 盘中快讯（单次返回最多）
  - mw_bulletins             Breaking News Bulletins 突发快讯
无独立正文（description 为空）的 feed 条目，将标题降级为 content，title 置空。

实现说明：
使用 page.request.get 通过浏览器上下文发起请求（完整浏览器指纹），
解析 RSS 2.0 XML（dc/media 为命名空间前缀，title/description 等为默认命名空间），
将四个 feed 的条目按发布时间（北京时间，字符串字典序即时间序）倒序合并取前 num 条。
"""

import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult

# dc 命名空间（author 字段），title/description/link 等在默认命名空间无需前缀
DC_NS = "http://purl.org/dc/elements/1.1/"


class MarketWatchFlashNewsParams(BaseModel):
    """市场观察新闻快讯参数模型"""

    num: int = Field(
        default=30,
        ge=1,
        le=60,
        description="获取快讯数量，默认30条，最大60条（四个 feed 聚合单次上限）",
    )


class MarketWatchFlashNewsSpider(BaseWebSpider):
    """
    市场观察（MarketWatch）新闻快讯 Spider

    聚合 MarketWatch 四个官方 RSS feed，按时间倒序取最新新闻快讯
    包括标题/摘要（无摘要则以标题为内容）、作者、发布时间、文章链接等信息
    """

    name = "marketwatch_flash_news"
    description = "聚合 MarketWatch 四个官方 feed 获取最新新闻快讯，按时间倒序，包括标题、摘要、作者、发布时间、链接等"
    version = "1.1.0"
    author = "noimank"
    platform = "市场观察"

    params_model = MarketWatchFlashNewsParams

    # MarketWatch 官方 RSS feed（公开，无需鉴权），聚合后按时间排序
    FEED_URLS = [
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
        "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
        "https://feeds.content.dowjones.io/public/rss/mw_bulletins",
    ]

    async def crawl(self, params: MarketWatchFlashNewsParams) -> SpiderResult:
        """
        爬取 MarketWatch 最新新闻快讯（四 feed 聚合、按时间倒序）

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("marketwatch") as page:
            all_items: list[dict[str, Any]] = []
            success_feed_count = 0

            for url in self.FEED_URLS:
                response = await page.request.get(url, timeout=30000)
                if response.status != 200:
                    continue
                success_feed_count += 1

                try:
                    root = ElementTree.fromstring(await response.text())
                except ElementTree.ParseError:
                    continue

                for item in root.findall(".//item"):
                    parsed = self._parse_news_item(item)
                    # 保留可排序（有时间戳）的条目
                    if parsed["pub_time"]:
                        all_items.append(parsed)

            if not all_items:
                return SpiderResult(
                    success=False,
                    message="四个 feed 均获取失败",
                )

            # pub_time 为 "YYYY-MM-DD HH:MM:SS" 北京时间，字符串字典序即时间序
            all_items.sort(key=lambda x: x["pub_time"], reverse=True)
            news_list = all_items[: params.num]

            return SpiderResult(
                success=True,
                data={
                    "total": len(news_list),
                    "news_list": news_list,
                },
                message=f"成功聚合 {success_feed_count}/4 个 feed，获取 {len(news_list)} 条快讯",
            )

    @staticmethod
    def _parse_news_item(item: ElementTree.Element) -> dict[str, Any]:
        """解析单条新闻快讯数据"""

        def _text(tag: str) -> str:
            node = item.find(tag)
            return (node.text or "").strip() if node is not None else ""

        # 标题/摘要含 HTML 实体（如 &#x2019; 弯引号），反转义并去除可能的内嵌标签
        title = html.unescape(re.sub(r"<[^>]+>", "", _text("title"))).strip()
        excerpt = html.unescape(re.sub(r"<[^>]+>", "", _text("description"))).strip()

        # RFC 2822 发布时间（如 "Fri, 14 Aug 2026 21:34:00 GMT"，GMT 即 UTC），转换为北京时间
        pub_time = ""
        pub_date = _text("pubDate")
        if pub_date:
            try:
                dt = parsedate_to_datetime(pub_date)
                pub_time = dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                pub_time = ""

        # 作者（dc:creator，带命名空间前缀；bulletins feed 无此字段）
        author = ""
        creator = item.find(f"{{{DC_NS}}}creator")
        if creator is not None and creator.text:
            author = creator.text.strip()

        # 文章链接去除 RSS 归属追踪参数（?mod=...）
        url = _text("link").split("?", 1)[0]

        # 无独立正文的 feed（realtimeheadlines/marketpulse/bulletins）将标题降级为内容，标题置空
        if not excerpt:
            excerpt, title = title, ""

        return {
            "title": title,
            "content": excerpt,
            # "author": author,
            "pub_time": pub_time,
            "url": url,
        }
