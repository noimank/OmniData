"""
选股宝7x24快讯 Spider
从选股宝获取实时财经快讯

通过 baoer-api.xuangubao.com.cn 接口获取数据
"""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class XuanguBaoFlashNewsParams(BaseModel):
    """选股宝快讯参数模型"""

    limit: int = Field(
        default=20,
        ge=1,
        le=50,
        description="获取快讯数量，默认20条，最大50条",
    )


class XuanguBaoFlashNewsSpider(BaseWebSpider):
    """
    选股宝7x24快讯 Spider

    从选股宝获取实时财经快讯列表
    包括快讯内容、发布时间、链接等信息
    """

    name = "xuangubao_flash_news"
    description = "获取选股宝7x24实时财经快讯，包括内容、时间、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "选股宝"

    params_model = XuanguBaoFlashNewsParams

    async def crawl(self, params: XuanguBaoFlashNewsParams) -> SpiderResult:
        try:
            async with self.new_page("xuangubao") as page:
                # 先访问页面建立上下文
                await page.goto(
                    "https://xuangutong.com.cn/live",
                    wait_until="domcontentloaded",
                    timeout=15000,
                )

                headers = {
                    "x-appgo-platform": "device=pc",
                    "x-track-info": '{"AppId":"com.xuangutong.web","AppVersion":"1.0.0"}',
                    "Referer": "https://xuangutong.com.cn/live",
                }

                # 尝试 newsflash 接口
                response = await page.request.get(
                    "https://baoer-api.xuangubao.com.cn/api/v6/message/newsflash",
                    params={
                        "limit": params.limit,
                        "subj_ids": "9,10,723,35,469",
                        "platform": "pcweb",
                    },
                    headers=headers,
                    timeout=15000,
                )

                json_data = await response.json()

                # newsflash 需要登录，回退使用研报快讯接口
                if json_data.get("code") != 20000:
                    return await self._fetch_reports(page, params, headers)

                messages = json_data.get("data", {}).get("messages", [])
                if not messages:
                    return await self._fetch_reports(page, params, headers)

                news_list = [self._parse_news_item(item) for item in messages]

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

    async def _fetch_reports(self, page, params, headers):
        """使用公开的研报快讯接口作为数据源"""
        response = await page.request.get(
            "https://baoer-api.xuangubao.com.cn/api/v6/report/reports/list",
            params={
                "limit": params.limit,
                "tag_ids": "",
                "category_ids": "",
            },
            headers=headers,
            timeout=15000,
        )

        if response.status != 200:
            return SpiderResult(
                success=False,
                message=f"请求失败，状态码：{response.status}",
            )

        json_data = await response.json()

        if json_data.get("code") != 20000:
            return SpiderResult(
                success=False,
                message=f"获取数据失败：{json_data.get('message', '未知错误')}",
            )

        items = json_data.get("data", {}).get("items", [])
        if not items:
            return SpiderResult(
                success=False,
                message="未获取到快讯数据",
            )

        news_list = [self._parse_report_item(item) for item in items]

        return SpiderResult(
            success=True,
            data={
                "total": len(news_list),
                "news_list": news_list,
            },
            message=f"成功获取 {len(news_list)} 条快讯",
        )

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """解析单条快讯数据"""
        content = item.get("content", "") or ""
        if content:
            content = re.sub(r"<[^>]+>", "", content).strip()

        title = item.get("title", "") or ""
        if not title and content:
            m = re.match(r"^【(.+?)】", content)
            if m:
                title = m.group(1)

        ctime = item.get("ctime", 0)
        pub_time = ""
        if ctime:
            try:
                dt = datetime.fromtimestamp(ctime)
                pub_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pub_time = str(ctime)

        return {
            "id": item.get("id", 0),
            "title": title,
            "content": content,
            "pub_time": pub_time,
            "url": item.get("target_url", "") or item.get("url", ""),
        }

    def _parse_report_item(self, item: dict) -> dict[str, Any]:
        """解析单条研报数据"""
        published_at = item.get("published_at", 0)
        pub_time = ""
        if published_at:
            try:
                dt = datetime.fromtimestamp(published_at)
                pub_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pub_time = str(published_at)

        tags = [t.get("name", "") for t in item.get("tags", [])]
        orgs = [o.get("name", "") for o in item.get("organizations", [])]

        return {
            "id": item.get("id", 0),
            "title": item.get("title", ""),
            "content": item.get("summary", ""),
            "pub_time": pub_time,
            "url": item.get("route", ""),
            "tags": tags,
            "organizations": orgs,
        }
