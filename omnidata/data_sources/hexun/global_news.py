"""
和讯网全球新闻资讯 Spider
获取和讯网7x24小时快讯新闻列表

从 https://opentool.hexun.com/MongodbNewsService/getNewsListByJson.jsp 接口获取数据
支持分页查询
"""

import json
import re
import random
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class HexunNewsParams(BaseModel):
    """和讯网快讯参数模型"""

    page: int = Field(
        default=1,
        ge=1,
        description="页码，默认第1页",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每页新闻数量，默认20条，最大100条",
    )


class HexunGlobalNewsSpider(BaseWebSpider):
    """
    和讯网全球新闻资讯 Spider

    从和讯网获取7x24小时快讯新闻列表
    包括新闻标题、摘要、发布时间、来源、链接、作者等信息
    """

    name = "hexun_global_news"
    description = "获取和讯网7x24小时快讯新闻列表，包括标题、摘要、发布时间、来源、链接等"
    version = "1.0.0"
    author = "noimank"
    platform = "和讯网"

    params_model = HexunNewsParams

    # API 配置
    API_URL = "https://opentool.hexun.com/MongodbNewsService/getNewsListByJson.jsp"
    NEWS_ID = "189223574"  # 7x24小时快讯频道ID

    async def crawl(self, params: HexunNewsParams) -> SpiderResult:
        """
        爬取和讯网快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("hexun") as page:
                # 生成随机 callback 名称
                callback_name = (
                    f"ptemplate_jsonp_{random.randint(100000000000000000, 999999999999999999)}"
                )

                # 构建请求参数
                request_params = {
                    "id": self.NEWS_ID,
                    "s": params.page_size,
                    "cp": params.page,
                    "callback": callback_name,
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

                # 解析新闻列表
                news_list = json_data.get("result", [])
                if not news_list:
                    return SpiderResult(
                        success=True,
                        data={
                            "page": params.page,
                            "page_size": params.page_size,
                            "total": 0,
                            "total_page": json_data.get("totalPage", 0),
                            "news_list": [],
                        },
                        message="暂无新闻数据",
                    )

                parsed_news = [self._parse_news_item(item) for item in news_list]

                return SpiderResult(
                    success=True,
                    data={
                        "page": params.page,
                        "page_size": params.page_size,
                        "total": len(parsed_news),
                        "total_page": json_data.get("totalPage", 0),
                        "total_number": json_data.get("totalNumber", 0),
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
            # 匹配 ptemplate_jsonp_xxx( {...}) 格式，注意可能有空格
            # 使用更简单的匹配方式：找到第一个 ( 和最后一个 )
            start_idx = response_text.find("(")
            end_idx = response_text.rfind(")")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx + 1 : end_idx].strip()
                return json.loads(json_str)
            # 如果直接是JSON格式
            return json.loads(response_text)
        except Exception:
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
            # "id": item.get("id", 0),
            "title": item.get("title", ""),
            "content": item.get("abstract", ""),
            "pub_time": item.get("entitytime", ""),
            "source": item.get("medianame", ""),
            # "author": item.get("author", ""),
            "url": item.get("entityurl", ""),
            # "image": item.get("newsmatchpic", ""),
            # "keywords": item.get("keyword", "").split(",") if item.get("keyword") else [],
        }
