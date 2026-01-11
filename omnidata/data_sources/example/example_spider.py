"""
示例爬虫
演示如何使用 BaseWebSpider 创建爬虫
"""

from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult


class ExampleParams(BaseModel):
    """示例爬虫参数模型"""

    url: HttpUrl = Field(..., description="要访问的URL")
    wait_for_selector: str = Field(default="body", description="等待的CSS选择器")
    screenshot: bool = Field(default=False, description="是否截图")


class ExampleSpider(BaseWebSpider):
    """
    示例爬虫

    演示了如何继承 BaseWebSpider 并实现 crawl 方法
    """

    name = "example_spider"
    description = "一个简单的示例爬虫，用于演示框架的使用方法"
    version = "1.0.0"
    author = "noimank"
    platform = "测试平台"

    # 定义参数模型
    params_model = ExampleParams

    async def crawl(self, params: ExampleParams) -> SpiderResult:
        """
        爬虫核心逻辑

        Args:
            params: 验证后的参数对象（ExampleParams 类型）

        Returns:
            SpiderResult: 执行结果
        """
        # 使用上下文管理器获取页面（推荐）
        async with self.get_context() as context:
            page = await context.new_page()
            # 访问目标 URL
            await page.goto(str(params.url))

            # 等待指定选择器
            await page.wait_for_selector(params.wait_for_selector)

            # 提取页面信息
            title = await page.title()
            url = page.url

            # 可选：截图
            screenshot_data = None
            if params.screenshot:
                screenshot_bytes = await page.screenshot(full_page=False)
                import base64

                screenshot_data = base64.b64encode(screenshot_bytes).decode("utf-8")

            return SpiderResult(
                success=True,
                data={
                    "title": title,
                    "url": url,
                    "screenshot": screenshot_data,
                    "timestamp": self._get_timestamp(),
                },
            )

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()


class NewsSpiderParams(BaseModel):
    """新闻爬虫参数示例"""

    category: str = Field(default="tech", description="新闻分类")
    limit: int = Field(default=10, ge=1, le=100, description="获取数量限制")


class NewsSpider(BaseWebSpider):
    """
    新闻爬虫示例

    演示了如何处理列表数据
    """

    name = "news_spider"
    description = "示例新闻爬虫，演示如何抓取列表数据"
    version = "1.0.0"
    author = "noimank"
    platform = "测试平台"

    # 定义参数模型
    params_model = NewsSpiderParams

    async def crawl(self, params: NewsSpiderParams) -> SpiderResult:
        """
        爬取新闻列表

        Args:
            params: 验证后的参数对象（NewsSpiderParams 类型）

        Returns:
            SpiderResult: 执行结果
        """
        # 这里是示例实现，实际需要根据目标网站结构调整
        # async with self.get_page_context() as page:
        #     await page.goto(f"https://example.com/news/{params.category}")

        # 示例：返回模拟数据
        news_list = []
        for i in range(min(params.limit, 5)):
            news_list.append(
                {
                    "title": f"News Item {i + 1}",
                    "category": params.category,
                    "url": f"https://example.com/news/{i + 1}",
                    "timestamp": self._get_timestamp(),
                }
            )

        return SpiderResult(
            success=True,
            data=news_list,
        )

    async def postprocess(self, result: SpiderResult, params: NewsSpiderParams) -> SpiderResult:
        """后处理：添加额外信息"""
        if result.data and isinstance(result.data, list):
            for item in result.data:
                item["processed_at"] = self._get_timestamp()
                item["spider_version"] = self.version
        return result

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()
