"""
东方财富全球财经快讯 Spider
获取东方财富全球财经快讯新闻列表

通过访问 https://kuaixun.eastmoney.com/ 触发对
https://np-weblist.eastmoney.com/comm/web/getFastNewsList 的真实请求，
用 page.route 拦截该请求、改写 fastColumn / pageSize 参数后再放行，
直接读取响应数据。整个流程以浏览器原生请求发出，
服务端看到的是带 cookie / referer / sec-ch-ua 等真实浏览器指纹的请求，
反爬风险最低。
"""

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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
    version = "1.2.0"
    author = "noimank"
    platform = "东方财富"

    params_model = EastmoneyFastNewsParams

    # 入口页面：访问后会自动向 getFastNewsList 发起请求
    PAGE_URL = "https://kuaixun.eastmoney.com/"
    # 目标接口
    API_HOST = "np-weblist.eastmoney.com"
    API_PATH = "/comm/web/getFastNewsList"

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

                # ── 拦截 getFastNewsList 请求 ──
                # 服务端对 cookie / referer / sec-ch-ua 等浏览器指纹敏感，
                # 通过 page.route 拦截后用 route.fetch(url=新URL) 改写参数再放行，
                # Playwright 会自动带上原始请求的所有请求头，伪装度最高。
                captured_body: dict[str, str | None] = {"body": None}

                async def handle_route(route):
                    url = route.request.url
                    if self.API_PATH in url and self.API_HOST in url:
                        # 改写 fastColumn / pageSize，保留其它字段（特别是 sortEnd= 空值）
                        new_url = self._rewrite_query(
                            url,
                            {
                                "fastColumn": params.fast_column,
                                "pageSize": str(params.page_size),
                            },
                        )
                        try:
                            response = await route.fetch(url=new_url)
                            captured_body["body"] = await response.text()
                            await route.fulfill(response=response)
                            return
                        except Exception:
                            # 改写失败则放行原始请求
                            await route.continue_()
                            return
                    await route.continue_()

                await page.route("**/*", handle_route)

                # 访问入口页，等待页面真正发起 getFastNewsList 请求
                await page.goto(self.PAGE_URL, timeout=30000)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)

                # 等待拦截到响应（最多 10 秒）
                for _ in range(20):
                    if captured_body["body"] is not None:
                        break
                    await page.wait_for_timeout(500)

                if captured_body["body"] is None:
                    return SpiderResult(
                        success=False,
                        message="拦截 getFastNewsList 响应超时，页面未发起该请求",
                    )

                # 解析 JSONP 响应
                json_data = self._parse_jsonp(captured_body["body"])
                if json_data is None:
                    return SpiderResult(
                        success=False,
                        message="解析响应数据失败：返回内容不是合法的 JSONP/JSON",
                    )

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

    @staticmethod
    def _rewrite_query(url: str, overrides: dict[str, str]) -> str:
        """
        改写 URL 的 query string，保留 keep_blank_values 的空值字段

        Args:
            url: 原始 URL
            overrides: 要覆盖的字段

        Returns:
            改写后的 URL
        """
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs.update({k: [v] for k, v in overrides.items()})
        new_query = urlencode(qs, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    def _parse_jsonp(self, raw_text: str) -> dict[str, Any] | None:
        """
        解析 JSONP / JSON 响应

        支持两种格式：
        - JSON: {"code": "1", ...}
        - JSONP: callback({"code": "1", ...}) / jQuery183..._123({"code": "1", ...});

        Args:
            raw_text: 原始响应文本

        Returns:
            解析后的字典，失败返回 None
        """
        if not raw_text:
            return None
        try:
            # 优先尝试直接解析为 JSON
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass

        # JSONP：匹配 "callback({...});" 形式
        match = re.search(r"\w+\s*\((.*)\)\s*;?\s*$", raw_text.strip(), re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
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
            "title": item.get("title", ""),
            "content": item.get("summary", ""),
            "pub_time": item.get("showTime", ""),
            "stock_list": item.get("stockList", []),
        }
