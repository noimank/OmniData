"""
新浪财经全球财经快讯 Spider
获取新浪财经7x24小时全球财经新闻列表

从 https://zhibo.sina.com.cn/api/zhibo/feed 接口获取数据
支持分页和标签筛选
"""

import json
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class SinaFinanceNewsParams(BaseModel):
    """新浪财经全球快讯参数模型"""

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
    tag_id: int = Field(
        default=0,
        description="标签ID，筛选新闻分类。0=全部, 1=宏观, 3=公司, 4=数据, "
        "5=市场, 6=观点, 7=央行, 8=其他, 10=A股, 102=国际",
    )


class SinaFinanceNewsSpider(BaseWebSpider):
    """
    新浪财经全球财经快讯 Spider

    从新浪财经7x24小时财经频道获取全球财经快讯新闻列表
    包括新闻内容、发布时间、来源等信息
    """

    name = "sina_finance_news"
    description = "获取新浪财经7x24小时全球财经快讯，支持按标签筛选（全部/宏观/公司/数据/市场/观点/央行/其他/A股/国际）"
    version = "1.0.0"
    author = "noimank"
    platform = "新浪财经"

    params_model = SinaFinanceNewsParams

    # API 配置
    API_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"
    ZHIBO_ID = "152"  # 全球财经频道

    # 标签映射
    TAG_MAP = {
        0: "全部",
        1: "宏观",
        3: "公司",
        4: "数据",
        5: "市场",
        6: "观点",
        7: "央行",
        8: "其他",
        10: "A股",
        102: "国际",
    }

    async def crawl(self, params: SinaFinanceNewsParams) -> SpiderResult:
        """
        爬取新浪财经全球快讯新闻列表

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        async with self.new_page("sina") as page:
            # 生成时间戳
            timestamp = int(datetime.now().timestamp() * 1000)

            # 构建请求参数
            request_params = {
                "page": params.page,
                "page_size": params.page_size,
                "zhibo_id": self.ZHIBO_ID,
                "tag_id": params.tag_id,
                "dire": "f",
                "dpc": "1",
                "_": timestamp + 1,
            }

            # 发送请求
            response = await page.request.get(self.API_URL, params=request_params, timeout=30000)

            if response.status != 200:
                return SpiderResult(success=False, message=f"请求失败，状态码：{response.status}")

            # 获取响应文本（JSONP格式）
            response_text = await response.text()

            # 解析JSONP响应
            json_data = self._parse_jsonp(response_text)
            if json_data is None:
                return SpiderResult(success=False, message="解析响应数据失败")

            # 检查返回状态
            result_status = json_data.get("result", {}).get("status", {})
            if result_status.get("code") != 0:
                return SpiderResult(
                    success=False,
                    message=f"获取数据失败：{result_status.get('msg', '未知错误')}",
                )

            # 解析新闻列表
            feed_data = json_data.get("result", {}).get("data", {}).get("feed", {})
            news_list = feed_data.get("list", [])
            parsed_news = [self._parse_news_item(item) for item in news_list]

            tag_name = self.TAG_MAP.get(params.tag_id, "未知")

            return SpiderResult(
                success=True,
                data={
                    "page": params.page,
                    "page_size": params.page_size,
                    "tag_id": params.tag_id,
                    "tag_name": tag_name,
                    "total": len(parsed_news),
                    "news_list": parsed_news,
                },
                message=f"成功获取 {len(parsed_news)} 条快讯新闻（标签：{tag_name}）",
            )

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
        # 从ext字段解析文档URL
        ext_str = item.get("ext", "{}")
        try:
            ext = json.loads(ext_str)
            doc_url = ext.get("docurl", "")
            doc_id = ext.get("docid", "")
        except Exception:
            doc_url = ""
            doc_id = ""

        return {
            # "id": item.get("id", 0),
            "content": item.get("rich_text", ""),
            "pub_time": item.get("create_time", "") or item.get("update_time", ""),
            # "update_time": item.get("update_time", ""),
            # "source": item.get("creator", ""),
            # "comment_id": item.get("commentid", ""),
            "url": doc_url,
            # "doc_id": doc_id,
            "tag": [tag.get("name", "") for tag in item.get("tag", [])],
        }
