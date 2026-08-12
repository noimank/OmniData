"""
第一财经快讯 Spider
获取第一财经24小时快讯新闻列表

从 https://www.yicai.com/api/ajax/getbrieflist 接口获取数据
支持分页查询
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class YicaiNewsParams(BaseModel):
    """第一财经快讯参数模型"""

    page: int = Field(
        default=1,
        ge=1,
        description="页码，默认第1页",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=50,
        description="每页新闻数量，默认20条，最大50条",
    )


class YicaiQuickNewsSpider(BaseWebSpider):
    """
    第一财经快讯 Spider

    从第一财经获取24小时快讯新闻列表
    包括新闻标题、内容、发布时间、链接等信息
    """

    name = "yicai_quick_news"
    description = "获取第一财经24小时快讯新闻列表，包括标题、内容、发布时间、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "第一财经"

    params_model = YicaiNewsParams

    # API 配置
    API_URL = "https://www.yicai.com/api/ajax/getbrieflist"
    WEB_URL = "https://www.yicai.com/brief/"

    async def crawl(self, params: YicaiNewsParams) -> SpiderResult:
        """
        爬取第一财经快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("yicai") as page:
                # 构建请求参数
                request_params = {
                    "page": params.page,
                    "pagesize": params.page_size,
                    "type": "0",
                    "id": "0",
                }

                # 发送请求
                response = await page.request.get(
                    self.API_URL, params=request_params, timeout=30000
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False, message=f"请求失败，状态码：{response.status}"
                    )

                # 获取响应JSON
                json_data = await response.json()

                # 第一财经直接返回数组，无需检查code
                if not isinstance(json_data, list):
                    return SpiderResult(success=False, message=f"响应数据格式异常")

                # 解析新闻列表
                parsed_news = [self._parse_news_item(item) for item in json_data]

                return SpiderResult(
                    success=True,
                    data={
                        "page": params.page,
                        "page_size": params.page_size,
                        "total": len(parsed_news),
                        "news_list": parsed_news,
                    },
                    message=f"成功获取 {len(parsed_news)} 条快讯新闻",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """
        解析单条快讯新闻数据

        Args:
            item: API返回的单条新闻数据

        Returns:
            解析后的新闻字典
        """
        # 优先使用 LiveTitle，其次使用 NewsTitle
        title = item.get("LiveTitle", "") or item.get("NewsTitle", "")

        # 清除内容中的 HTML 标签
        content = item.get("LiveContent", "")
        # 移除可能的 <b> 标签
        content = content.replace("<b>", "").replace("</b>", "")

        # 构建完整URL
        url = item.get("ShareUrl", "")
        if not url and item.get("url"):
            url = f"https://www.yicai.com{item['url']}"

        # 发布时间：ISO格式（2026-08-12T08:27:21）转为 2026-08-12 08:27:21
        pub_time = ""
        create_date = item.get("CreateDate", "")
        if create_date:
            try:
                pub_time = datetime.fromisoformat(create_date).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pub_time = create_date

        return {
            "title": title,
            "content": content,
            "pub_time": pub_time,
            "url": url,
            # "images": item.get("LiveImages", ""),
            # "id": item.get("LiveID", 0),
            # "is_important": item.get("IsImportant", False),
            # "news_hot": item.get("NewsHot", 0),
        }
