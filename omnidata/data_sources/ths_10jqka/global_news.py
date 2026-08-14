"""
同花顺全球资讯 Spider
获取同花顺全球财经快讯新闻列表

从 https://news.10jqka.com.cn/tapp/news/push/stock 接口获取数据
支持分页
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class ThsGlobalNewsParams(BaseModel):
    """同花顺全球资讯参数模型"""

    page: int = Field(
        default=1,
        ge=1,
        description="页码，默认第1页",
    )
    tag: str = Field(
        default="21101",
        description="标签筛选，支持的数字ID: "
        "21101=全部(默认), -21101=要闻, 21103=A股, 21105=港股, "
        "21107=美股, 21109=基金, 21111=观点, 34843=公告",
    )


class ThsGlobalNewsSpider(BaseWebSpider):
    """
    同花顺全球资讯 Spider

    从同花顺财经获取全球财经快讯新闻列表
    包括新闻标题、摘要、发布时间、链接等信息
    """

    name = "ths_10jqka_global_news"
    description = (
        "获取同花顺全球财经快讯新闻列表，支持按标签筛选（全部/要闻/A股/港股/美股/基金/观点/公告）"
    )
    version = "1.0.0"
    author = "noimank"
    platform = "同花顺10jqka"

    params_model = ThsGlobalNewsParams

    # API 配置
    API_URL = "https://news.10jqka.com.cn/tapp/news/push/stock"

    async def crawl(self, params: ThsGlobalNewsParams) -> SpiderResult:
        """
        爬取同花顺全球资讯快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("ths_10jqka") as page:
            # 如果有一天反爬更强了，把下面语句打开,防止直接接口请求导致跨域等错误
            # await page.goto("https://www.10jqka.com.cn/")
            # await page.wait_for_load_state("domcontentloaded")

            # 构建请求参数
            request_params = {
                "page": str(params.page),
                "tag": params.tag,
                "track": "website",
            }

            # 发送请求
            response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

            if response.status != 200:
                return SpiderResult(success=False, message=f"请求失败，状态码：{response.status}")

            # 获取响应数据
            json_data = await response.json()

            # 检查返回状态
            if json_data.get("status", 1) != 1:
                return SpiderResult(
                    success=False, message=f"获取数据失败：{json_data.get('msg', '未知错误')}"
                )

            # 解析新闻列表
            news_list = json_data.get("data", {}).get("list", [])
            parsed_news = [self._parse_news_item(item) for item in news_list]

            return SpiderResult(
                success=True,
                data={
                    "page": params.page,
                    "tag": params.tag if params.tag else "全部",
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
        # 解析时间戳
        rtime = item.get("rtime", "")
        if rtime:
            try:
                pub_time = datetime.fromtimestamp(int(rtime)).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pub_time = ""
        else:
            pub_time = ""

        return {
            "title": item.get("title", ""),
            "content": item.get("digest", ""),
            "pub_time": pub_time,
            "url": item.get("url", ""),
        }
