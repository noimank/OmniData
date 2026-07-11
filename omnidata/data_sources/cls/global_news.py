"""
财联社全球新闻资讯 Spider
获取财联社全球财经快讯新闻列表

从 https://www.cls.cn/nodeapi/telegraphList 接口获取数据
支持筛选重点新闻
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class CLSNewsParams(BaseModel):
    """财联社快讯参数模型"""

    symbol: str = Field(
        default="全部",
        description="筛选类型。全部=获取全部新闻，重点=仅获取A级和B级重点新闻",
    )
    rn: int = Field(
        default=50,
        ge=1,
        le=100,
        description="每页新闻数量，默认50条",
    )


class CLSNewsSpider(BaseWebSpider):
    """
    财联社全球财经快讯 Spider

    从财联社获取全球财经快讯新闻列表
    包括新闻标题、内容、发布时间、等级等信息
    """

    name = "cls_global_news"
    description = "获取财联社全球财经快讯，支持筛选重点新闻（全部/重点）"
    version = "1.1.0"
    author = "noimank"
    platform = "财联社"

    params_model = CLSNewsParams

    # API 配置
    API_URL = "https://www.cls.cn/api/cache"
    API_PARAMS = {
        "app": "CailianpressWeb",
        "name": "telegraph",
        "os": "web",
        "sv": "8.7.9",
    }

    async def crawl(self, params: CLSNewsParams) -> SpiderResult:
        try:
            async with self.new_page("cls") as page:
                query_params = {**self.API_PARAMS, "rn": str(params.rn)}
                qs = "&".join(f"{k}={v}" for k, v in query_params.items())
                await page.goto(f"{self.API_URL}?{qs}")
                await page.wait_for_load_state("domcontentloaded")

                json_data = await page.evaluate(
                    """() => {
                    try {
                        return JSON.parse(document.body.innerText);
                    } catch (e) {
                        return { errno: -1, msg: String(e) };
                    }
                }"""
                )

                if json_data.get("errno") != 0:
                    return SpiderResult(
                        success=False,
                        message=f"获取数据失败：{json_data.get('msg', '未知错误')}",
                    )

                roll_data = json_data.get("data", {}).get("roll_data", [])
                parsed_news = [self._parse_news_item(item) for item in roll_data]

                if params.symbol == "重点":
                    parsed_news = [n for n in parsed_news if n["level"] in ["A", "B"]]

                news_data = [
                    {
                        "title": item["title"],
                        "content": item["content"],
                        "pub_time": item["pub_time"],
                        "url": item["url"],
                    }
                    for item in parsed_news
                ]

                filter_type = "重点" if params.symbol == "重点" else "全部"
                return SpiderResult(
                    success=True,
                    data={
                        "symbol": params.symbol,
                        "filter_type": filter_type,
                        "total": len(news_data),
                        "news_list": news_data,
                    },
                    message=f"成功获取 {len(news_data)} 条快讯新闻（筛选：{filter_type}）",
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
        # 时间戳转换
        ctime = item.get("ctime", 0)
        if ctime:
            pub_time = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")
        else:
            pub_time = ""

        item_id = item.get("id", 0)
        return {
            "id": item_id,
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "level": item.get("level", ""),
            "pub_time": pub_time,
            "url": f"https://www.cls.cn/detail/{item_id}" if item_id else "",
        }
