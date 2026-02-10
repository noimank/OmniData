"""
测试浏览器上下文池模块
"""


import json
from unittest.mock import AsyncMock, patch

import pytest

from omnidata.core.browser_context_pool import (
    BrowserContextPool,
    close_browser_context_pool,
    get_browser_context_pool,
)
from omnidata.core.config import BrowserConfig


@pytest.fixture
async def browser_pool():
    """创建浏览器上下文池实例, 完成环境初始化"""
    pool = BrowserContextPool(BrowserConfig(headless=True))
    await pool.initialize()
    yield pool
    await pool.shutdown()


@pytest.fixture
def mock_redis():
    """Mock Redis 客户端"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


class TestBrowserContextPool:
    """测试浏览器上下文池"""

    @pytest.mark.asyncio
    async def test_initialize(self, browser_pool):
        """测试初始化"""
        assert browser_pool._is_initialized is True
        assert browser_pool._browser is not None
        assert browser_pool.context_count == 0

    @pytest.mark.asyncio
    async def test_get_context(self, browser_pool):
        """测试获取上下文"""
        context = await browser_pool.get_context()
        assert context is not None
        assert browser_pool.context_count == 1

    @pytest.mark.asyncio
    async def test_new_page(self, browser_pool):
        """测试通过 new_page 创建页面"""
        async with browser_pool.new_page() as page:
            assert page is not None
            # context 不应该关闭，但 page 会自动关闭
        assert browser_pool.context_count == 1

    @pytest.mark.asyncio
    async def test_get_context_with_namespace(self, browser_pool, mock_redis):
        """测试带 namespace 的 get_context"""
        with patch("omnidata.core.browser_context_pool.get_redis", return_value=mock_redis):
            context = await browser_pool.get_context(namespace="test_source")
            assert context is not None
            # 验证加载状态被调用
            mock_redis.get.assert_called_once_with("omnidata:context_state:test_source")

    @pytest.mark.asyncio
    async def test_save_context_state(self, browser_pool, mock_redis):
        """测试保存上下文状态"""
        with patch("omnidata.core.browser_context_pool.get_redis", return_value=mock_redis):
            context = await browser_pool.get_context(namespace="test_source")
            # 创建一个 page 并设置一些 cookie
            page = await context.new_page()
            await page.goto("about:blank")
            await page.close()

            # 手动调用保存
            await browser_pool.save_context_state(context, "test_source")

            # 验证 Redis 保存被调用（不设置 TTL）
            mock_redis.set.assert_called()
            call_args = mock_redis.set.call_args
            assert call_args[0][0] == "omnidata:context_state:test_source"

    @pytest.mark.asyncio
    async def test_remove_context(self, browser_pool):
        """测试移除 context"""
        context = await browser_pool.get_context(namespace="test_remove")
        assert browser_pool.context_count == 1

        # 移除 context
        await browser_pool.remove_context("test_remove")
        assert browser_pool.context_count == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, browser_pool):
        """测试获取统计信息"""
        stats = browser_pool.get_stats()
        assert "browser_count" in stats
        assert "context_count" in stats
        assert stats["browser_count"] == 1
        assert stats["context_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_contexts(self, browser_pool):
        """测试创建多个上下文"""
        context1 = await browser_pool.get_context()
        context2 = await browser_pool.get_context()

        # 两个 context 应该是不同的实例
        assert context1 is not context2
        assert browser_pool.context_count == 2


class TestGlobalBrowserContextPool:
    """测试全局浏览器上下文池"""

    @pytest.mark.asyncio
    async def test_get_browser_context_pool_singleton(self):
        """测试全局浏览器上下文池单例"""
        pool1 = get_browser_context_pool()
        pool2 = get_browser_context_pool()
        assert pool1 is pool2

        # 清理
        await close_browser_context_pool()

    @pytest.mark.asyncio
    async def test_close_browser_context_pool(self):
        """测试关闭全局浏览器上下文池"""
        pool = get_browser_context_pool()
        assert pool is not None

        await close_browser_context_pool()

        # 再次获取应该是新的实例
        new_pool = get_browser_context_pool()
        assert new_pool is not pool

        # 清理
        await close_browser_context_pool()


class TestContextStatePersistence:
    """测试上下文状态持久化"""

    @pytest.mark.asyncio
    async def test_save_and_load_state_cycle(self, browser_pool, mock_redis):
        """测试保存和加载状态循环"""
        saved_state = {
            "cookies": [
                {
                    "name": "session",
                    "value": "abc123",
                    "domain": ".example.com",
                    "path": "/",
                }
            ],
            "origins": [],
        }

        # 模拟保存（不设置 TTL）
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(saved_state))

        with patch("omnidata.core.browser_context_pool.get_redis", return_value=mock_redis):
            # 先保存
            context = await browser_pool.get_context(namespace="test")
            await browser_pool.save_context_state(context, "test")

            # 再创建一个新的 context（应该会加载状态）
            context2 = await browser_pool.get_context(namespace="test")
            # 验证加载被调用
            mock_redis.get.assert_called()

    @pytest.mark.asyncio
    async def test_load_state_with_no_existing_data(self, browser_pool, mock_redis):
        """测试加载不存在的状态"""
        mock_redis.get = AsyncMock(return_value=None)

        with patch("omnidata.core.browser_context_pool.get_redis", return_value= mock_redis):
            # 不应该抛出异常
            context = await browser_pool.get_context(namespace="nonexistent")
            assert context is not None

    @pytest.mark.asyncio
    async def test_state_persistence_with_namespace(self, browser_pool, mock_redis):
        """测试不同 namespace 的状态隔离"""
        mock_redis.get = AsyncMock(return_value=None)

        with patch("omnidata.core.browser_context_pool.get_redis", return_value=mock_redis):
            # 不同的 namespace 应该使用不同的 Redis key
            context1 = await browser_pool.get_context(namespace="source1")
            await browser_pool.save_context_state(context1, "source1")

            context2 = await browser_pool.get_context(namespace="source2")
            await browser_pool.save_context_state(context2, "source2")

            # 验证使用了不同的 key
            calls = mock_redis.set.call_args_list
            keys = [call[0][0] for call in calls]
            assert "omnidata:context_state:source1" in keys
            assert "omnidata:context_state:source2" in keys
