"""
格隆汇7x24快讯 Spider
从格隆汇获取实时财经快讯

通过 gelonghui.com/api/live-channels/{channel}/lives/v4 接口获取数据
"""

import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class GelonghuiFlashNewsParams(BaseModel):
    """格隆汇快讯参数模型"""

    limit: int = Field(
        default=20,
        ge=1,
        le=50,
        description="获取快讯数量，默认20条，最大50条",
    )
    channel: str = Field(
        default="all",
        description="频道ID：all(全部), popular(最热), international(国际), "
        "AStock(A股), HKStock(港股), USStock(美股), "
        "exchangeCommodity(商品外汇), ai(AI), fundLive(基金), "
        "debenture(债券), virtualAssets(虚拟资产)",
    )


class GelonghuiFlashNewsSpider(BaseWebSpider):
    """
    格隆汇7x24快讯 Spider

    从格隆汇获取实时财经快讯列表
    包括快讯内容、发布时间、链接、相关股票等信息
    """

    name = "gelonghui_flash_news"
    description = "获取格隆汇7x24实时财经快讯，包括内容、时间、链接、相关股票等"
    version = "1.0.0"
    author = "noimank"
    platform = "格隆汇"

    params_model = GelonghuiFlashNewsParams

    API_URL = "https://www.gelonghui.com/api/live-channels/{channel}/lives/v4"

    async def crawl(self, params: GelonghuiFlashNewsParams) -> SpiderResult:
        async with self.new_page("gelonghui") as page:
            # 先访问快讯页面获取 Cookie
            await page.goto("https://www.gelonghui.com/live")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except PlaywrightTimeoutError:
                # DOMContentLoaded 超时不影响后续流程
                pass

            api_url = self.API_URL.format(channel=params.channel)
            response = await page.request.get(
                api_url,
                params={
                    "category": "all",
                    "limit": str(params.limit),
                    "timestamp": str(int(time.time() * 1000)),
                },
                timeout=15000,
            )

            if response.status != 200:
                return SpiderResult(
                    success=False,
                    message=f"请求失败，状态码：{response.status}",
                )

            json_data = await response.json()

            items = json_data.get("result", [])
            if not items:
                return SpiderResult(
                    success=False,
                    message="未获取到快讯数据",
                )

            news_list = [self._parse_news_item(item) for item in items]

            return SpiderResult(
                success=True,
                data={
                    "total": len(news_list),
                    "news_list": news_list,
                },
                message=f"成功获取 {len(news_list)} 条快讯",
            )

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """解析单条快讯数据"""
        content = item.get("content", "") or ""

        # 内容清洗：去除 HTML 标签
        content = re.sub(r"<[^>]+>", "", content).strip()

        # 标题提取
        title = item.get("title", "") or ""
        if not title:
            m = re.match(r"^【(.+?)】", content)
            if m:
                title = m.group(1)

        # 时间戳转换（秒 → 可读格式）
        pub_time = ""
        create_timestamp = item.get("createTimestamp", 0)
        if create_timestamp:
            dt = datetime.fromtimestamp(create_timestamp, tz=timezone(timedelta(hours=8)))
            pub_time = dt.strftime("%Y-%m-%d %H:%M:%S")

        # 相关股票
        related_stocks = []
        for stock in item.get("relatedStocks") or []:
            related_stocks.append(
                {
                    "market": stock.get("market", ""),
                    "code": stock.get("code", ""),
                    "name": stock.get("name", ""),
                }
            )

        # 统计数据
        count = item.get("count", {})

        return {
            "id": item.get("id", 0),
            "title": title,
            "content": content,
            # "content_prefix": item.get("contentPrefix", ""),
            "pub_time": pub_time,
            "url": item.get("route", ""),
            # "level": item.get("level", 0),
            "source": (item.get("source") or {}).get("name", ""),
            "related_stocks": related_stocks,
            # "read_count": count.get("read", 0),
            # "comment_count": count.get("comment", 0),
            # "like_count": count.get("like", 0),
        }
