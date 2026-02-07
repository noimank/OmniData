"""
金融界全球新闻资讯 Spider
获取金融界24小时快讯新闻列表

从 https://gateway.jrj.com/jrj-news/news/queryNewsFlash 接口获取数据
"""

from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class JRJNewsFlashParams(BaseModel):
    """金融界快讯参数模型"""
    pass
    # 不支持以下参数
    # page_size: int = Field(
    #     default=50,
    #     ge=1,
    #     le=100,
    #     description="每页新闻数量，默认50条，最大100条",
    # )


class JRJNewsFlashSpider(BaseWebSpider):
    """
    金融界全球新闻资讯 Spider

    从金融界获取24小时快讯新闻列表
    包括新闻标题、内容、发布时间、来源、链接等
    """

    name = "jrj_news_flash"
    description = "获取金融界24小时快讯新闻列表，包括标题、内容、发布时间、来源、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "金融界"

    params_model = JRJNewsFlashParams

    # API 配置
    API_URL = "https://gateway.jrj.com/jrj-news/news/queryNewsFlash"
    WEB_URL = "https://24h.jrj.com.cn/newsFlash?jrjbq"

    async def crawl(self, params: JRJNewsFlashParams) -> SpiderResult:
        """
        爬取金融界快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("jrj") as page:
                # 先访问网页页面以获取必要的 cookies, 暂时不需要
                # await page.goto(self.WEB_URL)
                # await page.wait_for_load_state("domcontentloaded")

                # 构建请求参数
                request_data = {
                    # "pageSize": params.page_size,
                }

                # 发送 API 请求 (使用 POST 方法)
                response = await page.request.post(
                    self.API_URL,
                    data=request_data,
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
                if json_data.get("code") != 20000:
                    return SpiderResult(
                        success=False,
                        message=f"获取数据失败：{json_data.get('message', '未知错误')}"
                    )

                # 解析新闻列表
                news_list = json_data.get("data", {}).get("data", [])
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
        return {
            "title": item.get("title", ""),
            "content": item.get("detail", ""),
            "pub_time": item.get("makeDate", ""),
            "source": item.get("paperMediaSource", ""),
            "url": item.get("pcInfoUrl", "") or item.get("infoUrl", ""),
        }
