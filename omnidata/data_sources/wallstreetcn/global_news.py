"""
华尔街见闻全球快讯 Spider
获取华尔街见闻7x24小时快讯新闻列表

从 https://api-one-wscn.awtmt.com/apiv1/content/lives 接口获取数据
支持多频道查询
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class WallstreetcnNewsParams(BaseModel):
    """华尔街见闻快讯参数模型"""

    channel: Literal[
        "global",
        "a-stock",
        "us-stock",
        "hk-stock",
        "forex",
        "commodity",
        "bond",
        "tech",
    ] = Field(
        default="global",
        description="新闻频道：global-要闻，a-stock-A股，us-stock-美股，hk-stock-港股，forex-外汇，commodity-商品，bond-债券，tech-科技",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每次获取新闻数量，默认20条，最大100条",
    )


class WallstreetcnGlobalNewsSpider(BaseWebSpider):
    """
    华尔街见闻全球快讯 Spider

    从华尔街见闻获取7x24小时快讯新闻列表
    包括新闻标题、内容、发布时间、链接、作者等信息
    """

    name = "wallstreetcn_global_news"
    description = "获取华尔街见闻7x24小时快讯新闻列表，支持多频道筛选（要闻/A股/美股/港股/外汇/商品/债券/科技），包括标题、内容、发布时间、链接等"
    version = "1.1.0"
    author = "noimank"
    platform = "华尔街见闻"

    params_model = WallstreetcnNewsParams

    # API 配置
    API_URL = "https://api-one-wscn.awtmt.com/apiv1/content/lives"
    WEB_URL = "https://wallstreetcn.com/live/global"

    # 频道映射
    CHANNEL_MAP = {
        "global": "global-channel",
        "a-stock": "a-stock-channel",
        "us-stock": "us-stock-channel",
        "hk-stock": "xgb-channel",
        "forex": "forex-channel",
        "commodity": "commodity-channel",
        "bond": "bond-channel",
        "tech": "tech-channel",
    }

    async def crawl(self, params: WallstreetcnNewsParams) -> SpiderResult:
        """
        爬取华尔街见闻快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("wallstreetcn") as page:
            # 获取频道对应的API参数
            channel_param = self.CHANNEL_MAP.get(params.channel, "global-channel")

            # 构建请求参数
            request_params = {
                "channel": channel_param,
                "client": "pc",
                "limit": params.limit,
                "first_page": "true",
                "accept": "live,vip-live",
            }

            # 发送请求
            response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

            if response.status != 200:
                return SpiderResult(success=False, message=f"请求失败，状态码：{response.status}")

            # 获取响应JSON
            json_data = await response.json()

            # 检查返回状态
            if json_data.get("code") != 20000:
                return SpiderResult(
                    success=False,
                    message=f"获取数据失败：{json_data.get('message', '未知错误')}",
                )

            # 解析新闻列表
            news_list = json_data.get("data", {}).get("items", [])
            if not news_list:
                return SpiderResult(
                    success=True,
                    data={
                        "channel": params.channel,
                        "limit": params.limit,
                        "total": 0,
                        "news_list": [],
                    },
                    message="暂无新闻数据",
                )

            parsed_news = [self._parse_news_item(item) for item in news_list]

            return SpiderResult(
                success=True,
                data={
                    "channel": params.channel,
                    "limit": params.limit,
                    "total": len(parsed_news),
                    "news_list": parsed_news,
                },
                message=f"成功获取 {len(parsed_news)} 条快讯新闻",
            )

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """
        解析单条快讯新闻数据

        Args:
            item: API返回的单条新闻数据

        Returns:
            解析后的新闻字典
        """
        # 获取作者信息
        author_info = item.get("author", {})
        author_name = author_info.get("display_name", "") if author_info else ""

        # 处理发布时间（Unix 时间戳，秒）
        display_time = item.get("display_time", 0)
        pub_time = self._format_timestamp(display_time)

        return {
            "title": item.get("title", ""),
            "content": item.get("content_text", ""),
            "pub_time": pub_time,
            "url": item.get("uri", ""),
            # "author": author_name,
        }

    def _format_timestamp(self, timestamp: int) -> str:
        """
        格式化 Unix 时间戳为字符串

        Args:
            timestamp: Unix 时间戳（秒）

        Returns:
            格式化的时间字符串
        """
        if not timestamp:
            return ""
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(timestamp)
