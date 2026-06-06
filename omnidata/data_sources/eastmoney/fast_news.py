"""
东方财富全球财经快讯 Spider
获取东方财富全球财经快讯新闻列表

从 https://np-weblist.eastmoney.com/comm/web/getFastNewsList 接口获取数据
支持分页和每页数量设置
"""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class EastmoneyFastNewsParams(BaseModel):
    """全球财经快讯参数模型"""

    page_size: int = Field(
        default=50,
        ge=1,
        le=100,
        description="每页新闻数量，默认50条，最大100条",
    )
    fast_column: str = Field(
        default="102",
        description="快讯栏目代码，多个用逗号分割，如 '102,110,111'。"
        "101=焦点, 102=全球财经, 103=上市公司, 110=必读, 111=港股, "
        "112=外汇, 113=期货, 114=期权, 115=债券, 116=基金, 117=数据",
    )


class EastmoneyFastNewsSpider(BaseWebSpider):
    """
    东方财富全球财经快讯 Spider

    从东方财富网获取全球财经快讯新闻列表
    包括新闻标题、摘要、时间、评论数、分享数等信息
    """

    name = "eastmoney_fast_news"
    description = "获取东方财富全球财经快讯新闻列表，包括标题、摘要、时间、评论数、分享数等"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = EastmoneyFastNewsParams

    # API 配置
    API_URL = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"

    async def crawl(self, params: EastmoneyFastNewsParams) -> SpiderResult:
        """
        爬取全球财经快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])
                await page.goto("https://www.eastmoney.com/")

                # 构建请求参数
                timestamp = int(datetime.now().timestamp() * 1000)
                request_params = {
                    "client": "web",
                    "biz": "web_724",
                    "fastColumn": params.fast_column,
                    "sortEnd": "",
                    "pageSize": params.page_size,
                    "req_trace": timestamp,
                    "_": timestamp + 1,
                }

                # 发送请求
                response = await page.request.get(
                    self.API_URL, params=request_params, timeout=30000
                )

                if response.status != 200:
                    return SpiderResult(
                        success=False, message=f"请求失败，状态码：{response.status}"
                    )

                # 获取响应文本（JSONP格式）
                response_text = await response.text()

                # 解析JSONP响应
                json_data = self._parse_jsonp(response_text)
                if json_data is None:
                    return SpiderResult(success=False, message="解析响应数据失败")

                # 检查返回状态
                if json_data.get("code") != "1":
                    return SpiderResult(
                        success=False,
                        message=f"获取数据失败：{json_data.get('message', '未知错误')}",
                    )

                # 解析新闻列表
                news_list = json_data.get("data", {}).get("fastNewsList", [])
                parsed_news = [self._parse_news_item(item) for item in news_list]

                return SpiderResult(
                    success=True,
                    data={
                        "total": len(parsed_news),
                        "news_list": parsed_news,
                    },
                    message=f"成功获取 {len(parsed_news)} 条快讯新闻",
                )

        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_jsonp(self, response_text: str) -> dict[str, Any] | None:
        """
        解析JSONP格式响应

        Args:
            response_text: JSONP响应文本

        Returns:
            解析后的字典数据
        """
        try:
            # 匹配 jQuery18305328649312153803_1769931049465({...}) 格式
            match = re.search(r"jQuery\d+_\d+\(({.+})\)", response_text)
            if match:
                json_str = match.group(1)
                import json

                return json.loads(json_str)
            # 如果直接是JSON格式
            import json

            return json.loads(response_text)
        except Exception as e:
            return None

    def _parse_news_item(self, item: dict) -> dict[str, Any]:
        """
        解析单条快讯新闻数据

        Args:
            item: API返回的单条新闻数据

        Returns:
            解析后的新闻字典
        """
        return {
            # "code": item.get("code", ""),
            "title": item.get("title", ""),
            "content": item.get("summary", ""),
            "pub_time": item.get("showTime", ""),
            # "comment_count": item.get("pinglun_Num", 0),
            # "share_count": item.get("share", 0),
            "stock_list": item.get("stockList", []),
            # "image": item.get("image", []),
            # "title_color": item.get("titleColor", 0),
            # "real_sort": item.get("realSort", ""),
        }
