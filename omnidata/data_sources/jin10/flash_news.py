"""
金十数据快讯 Spider
从金十数据获取实时财经快讯

通过 flash-api.jin10.com 接口获取数据
"""

import re
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class Jin10FlashNewsParams(BaseModel):
    """金十数据快讯参数模型"""

    num: int = Field(
        default=20,
        ge=1,
        le=100,
        description="获取快讯数量，默认20条，最大100条",
    )


class Jin10FlashNewsSpider(BaseWebSpider):
    """
    金十数据快讯 Spider

    从金十数据获取实时财经快讯列表
    包括快讯内容、发布时间、类型等信息
    """

    name = "jin10_flash_news"
    description = "获取金十数据实时财经快讯，包括内容、时间、类型等"
    version = "1.0.0"
    author = "noimank"
    platform = "金十数据"

    params_model = Jin10FlashNewsParams

    # API 配置
    API_URL = "https://flash-api.jin10.com/get_flash_list"

    async def crawl(self, params: Jin10FlashNewsParams) -> SpiderResult:
        try:
            async with self.new_page("jin10") as page:
                response = await page.request.get(
                    self.API_URL,
                    params={
                        "channel": "-8200",
                        "vip": "1",
                        "num": str(params.num),
                    },
                    headers={
                        "x-app-id": "bVBF4FyRTn5NJF5n",
                        "x-version": "1.0.0",
                    },
                    timeout=30000,
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False,
                        message=f"请求失败，状态码：{response.status}",
                    )

                json_data = await response.json()

                if json_data.get("status") != 200:
                    return SpiderResult(
                        success=False,
                        message=f"获取数据失败：{json_data.get('message', '未知错误')}",
                    )

                flash_list = json_data.get("data", [])
                parsed_news = [
                    self._parse_news_item(item) for item in flash_list if item.get("time")
                ]

                return SpiderResult(
                    success=True,
                    data={
                        "total": len(parsed_news),
                        "news_list": parsed_news,
                    },
                    message=f"成功获取 {len(parsed_news)} 条快讯",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """解析单条快讯数据"""
        raw = item.get("data", {})

        # 内容清洗：去除 HTML 标签
        content = raw.get("content", "") or ""
        if content:
            content = re.sub(r"<[^>]+>", "", content).strip()

        # 标题：优先取 data.title，否则从 content 的【】中提取
        title = raw.get("title", "") or ""
        if not title and content:
            m = re.match(r"^【(.+?)】", content)
            if m:
                title = m.group(1)

        url = raw.get("source_link", "") or ""

        # 快讯类型：0=快讯, 1=数据指标, 2=文章
        flash_type = item.get("type", 0)
        type_map = {0: "快讯", 1: "数据", 2: "文章"}

        result = {
            "title": title,
            "content": content,
            "pub_time": item.get("time", ""),
            "url": url,
            # "type": type_map.get(flash_type, "其他"),
        }

        # 数据指标详情
        if flash_type == 1:
            result["data_detail"] = {
                "country": raw.get("country", ""),
                "name": raw.get("name", ""),
                "unit": raw.get("unit", ""),
                "previous": raw.get("previous", ""),
                "consensus": raw.get("consensus", ""),
                "actual": raw.get("actual", ""),
            }

        return result
