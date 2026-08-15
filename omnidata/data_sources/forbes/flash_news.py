"""
福布斯（Forbes）新闻快讯 Spider

从 Forbes 官方新闻推送接口获取实时新闻快讯列表

接口说明：
Forbes 没有公开的新闻 API，但官网首页前端实际调用
https://bacon.forbes.com/bacon-forbes-prd/genai/notifications-v2.json
获取新闻推送（快讯），该接口返回 JSON，无需鉴权。

实现说明：
使用 page.goto 以真实浏览器导航方式请求接口（完整浏览器指纹），
比 page.request.get 更稳定（后者偶发连接重置），直接读取响应 JSON。
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class ForbesFlashNewsParams(BaseModel):
    """福布斯新闻快讯参数模型"""

    num: int = Field(
        default=50,
        ge=1,
        le=200,
        description="获取快讯数量，默认50条，最大200条",
    )


class ForbesFlashNewsSpider(BaseWebSpider):
    """
    福布斯（Forbes）新闻快讯 Spider

    从 Forbes 官方新闻推送接口获取实时新闻快讯
    包括标题、内容、发布时间、文章链接等信息
    """

    name = "forbes_flash_news"
    description = "获取 Forbes 实时新闻快讯，包括标题、内容、发布时间、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "福布斯"

    params_model = ForbesFlashNewsParams

    # Forbes 官方新闻推送接口（首页 JS 实际调用，purge 为时间戳缓存刷新参数）
    API_URL = "https://bacon.forbes.com/bacon-forbes-prd/genai/notifications-v2.json"

    async def crawl(self, params: ForbesFlashNewsParams) -> SpiderResult:
        async with self.new_page("forbes") as page:
            # purge 为当前毫秒时间戳，用于绕过 CDN 缓存（与首页 JS 一致）
            response = await page.goto(
                f"{self.API_URL}?purge={int(time.time() * 1000)}",
                timeout=30000,
            )

            if response is None or response.status != 200:
                status = response.status if response else "无响应"
                return SpiderResult(
                    success=False,
                    message=f"请求失败，状态码：{status}",
                )

            json_data = await response.json()

            notification_list = json_data.get("aiNotifications", [])
            parsed_news = [self._parse_news_item(item) for item in notification_list[: params.num]]

            return SpiderResult(
                success=True,
                data={
                    "total": len(parsed_news),
                    "news_list": parsed_news,
                },
                message=f"成功获取 {len(parsed_news)} 条快讯",
            )

    @staticmethod
    def _parse_news_item(item: dict) -> dict[str, Any]:
        """解析单条新闻快讯数据"""
        # 接口无独立内容字段，content 即 title；title 为 null 时两者都为空字符串
        title = item.get("mainMessage") or ""

        # 时间戳转换（毫秒 → 北京时间）
        pub_time = ""
        timestamp_ms = int(item.get("timestamp", 0) or 0)
        if timestamp_ms:
            pub_time = datetime.fromtimestamp(
                timestamp_ms / 1000, tz=timezone(timedelta(hours=8))
            ).strftime("%Y-%m-%d %H:%M:%S")

        return {
            # "id": item.get("id", ""),
            "title": None,
            "content": title,
            "pub_time": pub_time,
            "url": item.get("linkUrl", ""),
        }
