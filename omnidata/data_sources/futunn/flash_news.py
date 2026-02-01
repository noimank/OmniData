"""
富途牛牛快讯 Spider
获取富途牛牛快讯新闻列表

从 https://news.futunn.com/news-site-api/main/get-flash-list 接口获取数据
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class FutuFlashNewsParams(BaseModel):
    """富途牛牛快讯参数模型"""

    page_size: int = Field(
        default=50,
        ge=1,
        le=100,
        description="每页新闻数量，默认50条，最大100条",
    )


class FutuFlashNewsSpider(BaseWebSpider):
    """
    富途牛牛快讯 Spider

    从富途牛牛获取快讯新闻列表
    包括新闻标题、内容、发布时间、链接等
    """

    name = "futunn_flash_news"
    description = "获取富途牛牛快讯新闻列表，包括标题、内容、发布时间、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "富途牛牛"

    params_model = FutuFlashNewsParams

    # API 配置
    API_URL = "https://news.futunn.com/news-site-api/main/get-flash-list"

    async def crawl(self, params: FutuFlashNewsParams) -> SpiderResult:
        """
        爬取富途牛牛快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("futunn") as page:
                # 构建请求参数
                request_params = {
                    "pageSize": str(params.page_size),
                }

                # 发送请求
                response = await page.request.get(
                    self.API_URL,
                    params=request_params,
                    timeout=30000
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False,
                        message=f"请求失败，状态码：{response.status}"
                    )

                # 获取响应JSON
                json_data = await response.json()

                # 检查返回状态
                if json_data.get("code") != 0:
                    return SpiderResult(
                        success=False,
                        message=f"获取数据失败：{json_data.get('msg', '未知错误')}"
                    )

                # 解析新闻列表
                news_list = json_data.get("data", {}).get("data", {}).get("news", [])
                parsed_news = [self._parse_news_item(item) for item in news_list]

                return SpiderResult(
                    success=True,
                    data={
                        "total": len(parsed_news),
                        "news_list": parsed_news,
                    },
                    message=f"成功获取 {len(parsed_news)} 条快讯新闻"
                )

        except Exception as e:
            return SpiderResult(
                success=False,
                message=f"爬取失败：{str(e)}"
            )

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """
        解析单条快讯新闻数据

        Args:
            item: API返回的单条新闻数据

        Returns:
            解析后的新闻字典
        """
        # 时间戳转换
        time_str = item.get("time", "")
        if time_str and time_str.isdigit():
            pub_time = datetime.fromtimestamp(int(time_str)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            pub_time = ""

        return {
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "pub_time": pub_time,
            "url": item.get("detailUrl", ""),
        }
