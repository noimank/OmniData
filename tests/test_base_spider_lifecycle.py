"""
测试 BaseWebSpider 生命周期：异常兜底、page 关闭保证、审计字段
"""

import pytest
from pydantic import BaseModel

from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult


class DummyParams(BaseModel):
    """测试参数模型"""

    url: str = "about:blank"


class FailingSpider(BaseWebSpider):
    """crawl 中抛异常的测试爬虫"""

    name = "test_failing_spider"
    platform = "测试平台"

    params_model = DummyParams

    async def crawl(self, params: DummyParams) -> SpiderResult:
        async with self.new_page() as page:
            raise RuntimeError("boom")


class OkSpider(BaseWebSpider):
    """正常返回的测试爬虫"""

    name = "test_ok_spider"
    platform = "测试平台"

    params_model = DummyParams

    async def crawl(self, params: DummyParams) -> SpiderResult:
        async with self.new_page() as page:
            await page.goto("about:blank")
            return SpiderResult(success=True, data={"title": await page.title()})


class TestBaseSpiderLifecycle:
    """测试爬虫基类生命周期"""

    @pytest.fixture
    async def browser_pool(self):
        from omnidata.core.browser_context_pool import BrowserContextPool
        from omnidata.core.config import BrowserConfig

        pool = BrowserContextPool(BrowserConfig(headless=True))
        await pool.initialize()
        yield pool
        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_exception_becomes_error_result(self, browser_pool):
        """crawl 抛异常时 run() 应返回 error result 而非向上抛"""
        spider = FailingSpider(browser_context_pool=browser_pool)
        result = await spider.run({"url": "about:blank"})

        assert result.success is False
        assert "boom" in (result.message or "")
        assert result.spider_name == "test_failing_spider"
        assert result.completed_at is not None
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_page_closed_after_exception(self, browser_pool):
        """crawl 异常后 page 必须被关闭，不产生泄漏"""
        spider = FailingSpider(browser_context_pool=browser_pool)
        await spider.run({"url": "about:blank"})

        # 计数归零说明所有 new_page 都走完了 finally
        assert browser_pool._active_pages == 0
        # context 池中不应残留未关闭的 page
        for metadata in browser_pool._contexts.values():
            assert len(metadata.context.pages) == 0

    @pytest.mark.asyncio
    async def test_validation_error_returns_error_result(self, browser_pool):
        """参数校验失败应返回 error result"""
        spider = OkSpider(browser_context_pool=browser_pool)
        result = await spider.run({"url": 12345})  # 类型错误

        assert result.success is False

    @pytest.mark.asyncio
    async def test_successful_run_sets_fields(self, browser_pool):
        """成功执行应自动填充 spider_name 与时间字段"""
        spider = OkSpider(browser_context_pool=browser_pool)
        result = await spider.run({})

        assert result.success is True
        assert result.spider_name == "test_ok_spider"
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds >= 0
        assert browser_pool._active_pages == 0
