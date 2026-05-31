"""
雪球7x24快讯 Spider
从雪球网获取实时财经快讯

通过 xueqiu.com/statuses/livenews/list.json 接口获取数据
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class XueqiuFlashNewsParams(BaseModel):
    """雪球快讯参数模型"""

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="获取快讯数量，默认10条，最大50条（API单次最多返回10条，超出会自动分页）",
    )


class XueqiuFlashNewsSpider(BaseWebSpider):
    """
    雪球7x24快讯 Spider

    从雪球网获取实时财经快讯列表
    包括快讯内容、发布时间、链接等信息
    """

    name = "xueqiu_flash_news"
    description = "获取雪球7x24实时财经快讯，包括内容、时间、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "雪球"

    params_model = XueqiuFlashNewsParams

    API_URL = "https://xueqiu.com/statuses/livenews/list.json"

    async def crawl(self, params: XueqiuFlashNewsParams) -> SpiderResult:
        try:
            async with self.new_page("xueqiu") as page:
                # 先访问雪球首页获取 Cookie
                await page.goto(
                    "https://xueqiu.com/",
                    wait_until="domcontentloaded",
                    timeout=15000,
                )

                response = await page.request.get(
                    self.API_URL,
                    params={
                        "since_id": "-1",
                        "max_id": "-1",
                        "count": str(params.limit),
                    },
                    timeout=15000,
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False,
                        message=f"请求失败，状态码：{response.status}",
                    )

                json_data = await response.json()

                items = json_data.get("items", [])
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

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """解析单条快讯数据"""
        text = item.get("text", "") or ""

        # 内容清洗：去除 HTML 标签
        content = re.sub(r"<[^>]+>", "", text).strip()

        # 从【】中提取标题
        title = ""
        m = re.match(r"^【(.+?)】", content)
        if m:
            title = m.group(1)

        # 时间戳转换（毫秒 → 可读格式）
        created_at = item.get("created_at", 0)
        pub_time = ""
        if created_at:
            dt = datetime.fromtimestamp(created_at / 1000, tz=timezone(timedelta(hours=8)))
            pub_time = dt.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "id": item.get("id", 0),
            "title": title,
            "content": content,
            "pub_time": pub_time,
            "url": item.get("target", ""),
            "view_count": item.get("view_count", 0),
            "reply_count": item.get("reply_count", 0),
            "share_count": item.get("share_count", 0),
        }
