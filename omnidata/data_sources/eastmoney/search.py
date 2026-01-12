"""
东方财富网通用搜索 Spider
通过拦截 search-api-web 接口获取搜索结果
支持资讯、公告、研报、问董秘四种搜索类型
"""

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class SearchParams(BaseModel):
    """东方财富搜索参数模型"""

    keyword: str = Field(..., min_length=1, description="搜索关键词")
    search_type: Literal["news", "ann", "report", "qa"] = Field(
        default="news",
        description="搜索类型：news=资讯, ann=公告, report=研报, qa=问董秘"
    )


class EastMoneySearchSpider(BaseWebSpider):
    """
    东方财富通用搜索 Spider

    通过拦截 search-api-web.eastmoney.com API 获取搜索结果
    """

    name = "eastmoney_search"
    description = "东方财富网通用搜索，支持资讯、公告、研报、问董秘四种搜索类型"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = SearchParams

    # 搜索类型映射（type 参数和结果字段）
    SEARCH_TYPE_MAP = {
        "news": ("cmsArticleWebOld", "https://so.eastmoney.com/news/s"),
        "ann": ("noticeWeb", "https://so.eastmoney.com/ann/s"),
        "report": ("researchReport", "https://so.eastmoney.com/yanbao/s"),
        "qa": ("wenDongMiWeb", "https://so.eastmoney.com/qa/s"),
    }

    async def crawl(self, params: SearchParams) -> SpiderResult:
        """
        爬取东方财富搜索结果

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """

        context = await self.get_context_simple("eastmoney")
        page = await context.new_page()
        try:
            await self.apply_anti_detection_scripts(page, "advanced")

            # 用于存储拦截到的数据
            captured_response = None

            # 拦截 API 请求
            async def handle_route(route):
                """拦截并处理 API 请求"""
                nonlocal captured_response
                try:
                    url = route.request.url
                    # 拦截搜索 API,可能会有多个，但只要有title字段就是有效的
                    if "search-api-web.eastmoney.com/search/jsonp" in url:
                        response = await route.fetch()
                        body = await response.body()
                        # 检查是否为 JSONP 响应，是包含title的通用搜索类型
                        api_data_temp = self._parse_jsonp(body)
                        results_t = api_data_temp.get("result", {})
                        data_valid = False
                        for k,v in results_t.items():
                            if isinstance(v, list):
                                if len(v) > 0:
                                    item = v[0]
                                    if isinstance(item, dict):
                                        if item.get("title"):
                                            data_valid = True
                                            break

                        if data_valid:
                            captured_response = body
                        # 中断请求，避免页面继续加载
                        # await route.abort()
                        await route.continue_()
                    else:
                        await route.continue_()
                except Exception:
                    await route.continue_()

            # 设置路由拦截
            await page.route("**/*", handle_route)

            # 获取搜索类型配置（智能解析无需手动指定 result_field）
            _, search_url = self.SEARCH_TYPE_MAP.get(params.search_type, self.SEARCH_TYPE_MAP["news"])

            # 构建搜索 URL
            url = f"{search_url}?keyword={params.keyword}"
            await page.goto(url)

            # 等待 API 响应被拦截（最多等待 10 秒）
            await page.wait_for_load_state("domcontentloaded")

            # 检查是否成功获取数据
            if captured_response is None:
                return SpiderResult(
                    success=False,
                    message="获取数据失败，该查询条件下无结果"
                )

            # 解析 JSONP 响应
            api_data = self._parse_jsonp(captured_response)
            if api_data is None:
                return SpiderResult(
                    success=False,
                    message="解析数据失败：无法解析 JSONP 响应"
                )

            # 检查响应状态
            if api_data.get("code") != 0:
                return SpiderResult(
                    success=False,
                    message=f"API 返回错误: {api_data.get('msg', 'Unknown error')}"
                )

            # 提取搜索结果（智能递归解析，无需手动指定 result_field）
            results_list = self._find_result_items(api_data)

            if not results_list:
                return SpiderResult(
                    success=True,
                    data=[],
                    message=f"未找到关键词 '{params.keyword}' 的搜索结果"
                )

            # 转换为统一格式（只保留序号、标题、内容、时间）
            results = []
            for index, item in enumerate(results_list, 1):
                results.append({
                    "序号": index,
                    "标题": self._clean_html(item.get("title", "")),
                    "内容": self._clean_html(item.get("content", "")),
                    "时间": item.get("date", ""),
                })


            return SpiderResult(
                success=True,
                data=results,
                message=f"成功获取 {len(results)} 条搜索结果"
            )
        except Exception as e:
            return SpiderResult(
                success=False,
                message=f"搜索失败: {str(e)}"
            )
        finally:
            await page.close()
            await context.close()

    @staticmethod
    def _parse_jsonp(body: bytes) -> dict | None:
        """
        解析 JSONP 格式的响应数据

        Args:
            body: 响应体字节数据

        Returns:
            解析后的字典，解析失败返回 None
        """
        try:
            text = body.decode("utf-8")
            # 提取括号内的 JSON 数据
            # 格式：jQuery1234567890({...})
            start_idx = text.find("(")
            end_idx = text.rfind(")")
            if start_idx > 0 and end_idx > start_idx:
                json_text = text[start_idx + 1:end_idx]
                return json.loads(json_text)
            return None
        except Exception:
            return None

    @staticmethod
    def _find_result_items(data: dict | list | None) -> list[dict] | None:
        """
        递归查找包含 title 字段的项目列表

        """
        if data is None:
            return None

        result = data.get("result", {})
        item_list = None
        #找到具有title的列表
        for key,value in result.items():
            if isinstance(value, list):
                if any("title" in item for item in value):
                    item_list = value
                    break
        return item_list




    @staticmethod
    def _clean_html(text: str) -> str:
        """
        清理 HTML 标签

        Args:
            text: 包含 HTML 标签的文本

        Returns:
            清理后的纯文本
        """
        if not text:
            return ""
        # 移除 <em> 标签
        text = re.sub(r"<em[^>]*>|</em>", "", text)
        # 移除其他 HTML 标签
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

