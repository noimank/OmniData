"""
界面新闻7x24快讯 Spider
从界面新闻获取实时财经快讯

通过 papi.jiemian.com/page/api/kuaixun/getLastest 接口获取数据
"""

import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class JiemianFlashNewsParams(BaseModel):
    """界面新闻快讯参数模型"""

    limit: int = Field(
        default=20,
        ge=1,
        le=50,
        description="获取快讯数量，默认20条，最大50条",
    )


class JiemianFlashNewsSpider(BaseWebSpider):
    """
    界面新闻7x24快讯 Spider

    从界面新闻获取实时财经快讯列表
    包括快讯标题、内容、发布时间、链接等信息
    """

    name = "jiemian_flash_news"
    description = "获取界面新闻7x24实时财经快讯，包括标题、内容、时间、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "界面新闻"

    params_model = JiemianFlashNewsParams

    API_URL = "https://papi.jiemian.com/page/api/kuaixun/getLastest"

    # 界面新闻快讯频道参数
    CID = "1323kb"
    TAGID = "1323"

    async def crawl(self, params: JiemianFlashNewsParams) -> SpiderResult:
        try:
            async with self.new_page("jiemian") as page:
                # 先访问快讯页面建立上下文
                await page.goto(
                    "https://www.jiemian.com/lists/4.html",
                    wait_until="domcontentloaded",
                    timeout=15000,
                )

                # 使用当前时间减去24小时作为 end_time，获取最近的快讯
                end_time = int(time.time()) - 86400

                response = await page.request.get(
                    self.API_URL,
                    params={
                        "cid": self.CID,
                        "tagid": self.TAGID,
                        "end_time": str(end_time),
                    },
                    headers={
                        "Referer": "https://www.jiemian.com/lists/4.html",
                    },
                    timeout=15000,
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False,
                        message=f"请求失败，状态码：{response.status}",
                    )

                json_data = await response.json()

                if json_data.get("code") != "0":
                    return SpiderResult(
                        success=False,
                        message=f"获取数据失败：{json_data.get('message', '未知错误')}",
                    )

                items = json_data.get("result", [])
                if not items:
                    return SpiderResult(
                        success=False,
                        message="未获取到快讯数据",
                    )

                # 按发布时间降序排列，取前 limit 条
                items = sorted(
                    items,
                    key=lambda x: int(x.get("publishtime", 0)),
                    reverse=True,
                )[: params.limit]

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
        title = item.get("title", "") or ""
        content = item.get("summary", "") or ""

        # 内容清洗：去除 HTML 标签
        if content:
            content = re.sub(r"<[^>]+>", "", content).strip()

        # 时间戳转换
        pub_time = ""
        publishtime = item.get("publishtime", "0")
        if publishtime:
            try:
                ts = int(publishtime)
                dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
                pub_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                pub_time = str(publishtime)

        article_id = item.get("id", "")
        url = f"https://www.jiemian.com/article/{article_id}.html" if article_id else ""

        return {
            "id": article_id,
            "title": title,
            "content": content,
            "pub_time": pub_time,
            "url": url,
        }
