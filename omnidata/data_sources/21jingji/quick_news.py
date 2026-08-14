"""
21财经快讯 Spider
获取21财经24小时快讯新闻列表

从 https://api.21jingji.com/timestream/getListweb 接口获取数据
支持分页查询
"""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class JingjiNewsParams(BaseModel):
    """21财经快讯参数模型"""

    page: int = Field(
        default=1,
        ge=1,
        description="页码，默认第1页",
    )


class JingjiQuickNewsSpider(BaseWebSpider):
    """
    21财经快讯 Spider

    从21财经获取24小时快讯新闻列表
    包括新闻标题、内容、发布时间、链接等
    """

    name = "21jingji_quick_news"
    description = "获取21财经24小时快讯新闻列表，包括标题、内容、发布时间、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "21财经"

    params_model = JingjiNewsParams

    # API 配置
    API_URL = "https://api.21jingji.com/timestream/getListweb"
    WEB_URL = "https://www.21jingji.com/channel/politics/"

    async def crawl(self, params: JingjiNewsParams) -> SpiderResult:
        """
        爬取21财经快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("21jingji") as page:
            # 构建请求参数
            request_params = {
                "page": params.page,
            }

            # 发送请求
            response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

            if response.status != 200:
                return SpiderResult(success=False, message=f"请求失败，状态码：{response.status}")

            # 获取响应文本（JSONP格式）
            text_data = await response.text()

            # 解析 JSONP 格式：提取 callback({...}) 中的 JSON
            json_data = self._parse_jsonp(text_data)
            if json_data is None:
                return SpiderResult(success=False, message=f"响应数据格式异常，无法解析 JSONP")

            # 解析新闻列表
            news_list = json_data.get("list", [])
            parsed_news = [self._parse_news_item(item) for item in news_list]

            return SpiderResult(
                success=True,
                data={
                    "page": params.page,
                    "total": len(parsed_news),
                    "news_list": parsed_news,
                },
                message=f"成功获取 {len(parsed_news)} 条快讯新闻",
            )

    def _parse_jsonp(self, text: str) -> dict | None:
        """
        解析 JSONP 格式响应

        Args:
            text: JSONP 格式的文本

        Returns:
            解析后的字典，解析失败返回 None
        """
        try:
            # 匹配 jQuery...({...}) 或 callback({...}) 格式
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                import json

                return json.loads(match.group())
            return None
        except Exception:
            return None

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """
        解析单条快讯新闻数据

        Args:
            item: API返回的单条新闻数据

        Returns:
            解析后的新闻字典
        """
        # 发布时间：源数据为 %Y-%m-%d %H:%M（分钟精度），补秒统一为 %Y-%m-%d %H:%M:%S
        pub_time = ""
        inputtime = item.get("inputtime", "")
        if inputtime:
            try:
                pub_time = datetime.strptime(inputtime, "%Y-%m-%d %H:%M").strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                pub_time = inputtime

        return {
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "pub_time": pub_time,
            "url": item.get("url", ""),
            # "source": item.get("source", ""),
            # "author": item.get("author", ""),
        }
