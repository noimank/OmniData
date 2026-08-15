"""
财富（Fortune）新闻快讯 Spider

从 Fortune 官方 WordPress REST API 获取最新新闻快讯列表

接口说明：
Fortune 官网基于 WordPress VIP 构建，其公开的 REST API
https://fortune.com/wp-json/wp/v2/posts 无需鉴权即可返回最新文章 JSON，
支持 per_page / _fields / page 等参数，可直接获取结构化新闻数据。

实现说明：
使用 page.request.get 通过浏览器上下文发起请求（完整浏览器指纹），
避免裸 HTTP 客户端被 UA 拦截（curl 等 UA 返回 403）。
"""

import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class FortuneFlashNewsParams(BaseModel):
    """财富新闻快讯参数模型"""

    num: int = Field(
        default=30,
        ge=1,
        le=100,
        description="获取快讯数量，默认30条，最大100条（WordPress 接口单页上限）",
    )


class FortuneFlashNewsSpider(BaseWebSpider):
    """
    财富（Fortune）新闻快讯 Spider

    从 Fortune 官方 WordPress REST API 获取最新新闻快讯
    包括标题、摘要、发布时间、文章链接等信息
    """

    name = "fortune_flash_news"
    description = "获取 Fortune 最新新闻快讯，包括标题、摘要、发布时间、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "财富"

    params_model = FortuneFlashNewsParams

    # Fortune 官方 WordPress REST API（公开，无需鉴权）
    API_URL = "https://fortune.com/wp-json/wp/v2/posts"

    async def crawl(self, params: FortuneFlashNewsParams) -> SpiderResult:
        """
        爬取 Fortune 最新新闻快讯列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("fortune") as page:
            # _fields 裁剪响应字段，仅返回解析所需数据，避免拉取全文正文
            response = await page.request.get(
                self.API_URL,
                params={
                    "per_page": params.num,
                    "_fields": "id,date_gmt,link,title,excerpt",
                },
                timeout=30000,
            )

            if response.status != 200:
                return SpiderResult(
                    success=False,
                    message=f"请求失败，状态码：{response.status}",
                )

            posts = await response.json()

            if not isinstance(posts, list):
                return SpiderResult(
                    success=False,
                    message="接口返回数据格式异常",
                )

            parsed_news = [self._parse_news_item(item) for item in posts]

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
        # 标题含 HTML 实体（如 &#8217; 弯引号），需反转义
        title = html.unescape(item.get("title", {}).get("rendered", "") or "")

        # 摘要去除 HTML 标签后反转义
        excerpt_html = item.get("excerpt", {}).get("rendered", "") or ""
        excerpt = html.unescape(re.sub(r"<[^>]+>", "", excerpt_html)).strip()

        # date_gmt 为 UTC 时间（无时区后缀），转换为北京时间
        pub_time = ""
        date_gmt = item.get("date_gmt", "")
        if date_gmt:
            try:
                dt = datetime.fromisoformat(date_gmt).replace(tzinfo=timezone.utc)
                pub_time = dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pub_time = ""

        return {
            "title": title,
            "content": excerpt,
            "pub_time": pub_time,
            "url": item.get("link", ""),
        }
