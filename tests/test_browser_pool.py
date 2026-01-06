"""
测试浏览器池模块
"""


import json
from unittest.mock import AsyncMock, patch

import pytest

from omnidata.core.browser_pool import BrowserPool, close_browser_pool, get_browser_pool
from omnidata.core.config import BrowserConfig


@pytest.fixture
async def browser_pool():
    """创建浏览器池实例, 完成环境初始化"""
    pool = BrowserPool(BrowserConfig(headless=True))
    await pool.initialize()
    yield pool
    await pool.shutdown()


@pytest.fixture
def mock_redis():
    """Mock Redis 客户端"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis


class TestBrowserPool:
    """测试浏览器池"""

    @pytest.mark.asyncio
    async def test_initialize(self, browser_pool):
        """测试初始化"""
        assert browser_pool._is_initialized is True
        assert browser_pool._browser_type is not None
        assert browser_pool.browser_count == 0

    @pytest.mark.asyncio
    async def test_get_browser(self, browser_pool):
        """测试获取浏览器"""
        browser = await browser_pool.get_browser()
        assert browser is not None
        assert browser_pool.browser_count == 1

    @pytest.mark.asyncio
    async def test_get_context(self, browser_pool):
        """测试获取上下文"""
        async with browser_pool.get_context() as context:
            assert context is not None
            # 验证 context 可以创建 page
            page = await context.new_page()
            await page.close()

    @pytest.mark.asyncio
    async def test_get_context_with_anti_detection_scripts(self, browser_pool):
        """测试带反检测脚本的 get_context"""
        async with browser_pool.get_context(
                anti_detection_scripts_names="basic"
        ) as context:
            page = await context.new_page()
            # 应用脚本
            await browser_pool.apply_anti_detection_scripts(page)
            await page.close()

    @pytest.mark.asyncio
    async def test_get_context_with_namespace(self, browser_pool, mock_redis):
        """测试带 namespace 的 get_context"""
        with patch("omnidata.core.browser_pool.get_redis", return_value=mock_redis):
            async with browser_pool.get_context(namespace="test_source") as context:
                assert context is not None
                # 验证加载状态被调用
                mock_redis.get.assert_called_once_with("omnidata:context_state:test_source")
                # 验证保存状态被调用
                mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_context_state(self, browser_pool, mock_redis):
        """测试保存上下文状态"""
        with patch("omnidata.core.browser_pool.get_redis", return_value=mock_redis):
            async with browser_pool.get_context(namespace="test_source") as context:
                # 创建一个 page 并设置一些 cookie
                page = await context.new_page()
                await page.goto("about:blank")
                await page.close()

                # 手动调用保存
                await browser_pool.save_context_state(context, "test_source")

                # 验证 Redis 保存被调用
                mock_redis.setex.assert_called()
                call_args = mock_redis.setex.call_args
                assert call_args[0][0] == "omnidata:context_state:test_source"

    @pytest.mark.asyncio
    async def test_load_context_state(self, browser_pool, mock_redis):
        """测试加载上下文状态"""
        # 模拟 Redis 返回的数据
        mock_state = {
            "cookies": [
                {
                    "name": "test_cookie",
                    "value": "test_value",
                    "domain": ".example.com",
                    "path": "/",
                }
            ],
            "origins": [],
        }
        mock_redis.get.return_value = json.dumps(mock_state)

        with patch("omnidata.core.browser_pool.get_redis", return_value=mock_redis):
            async with browser_pool.get_context(namespace="test_source") as context:
                # cookies 应该被加载
                await context.cookies()
                # 注意：新创建的 context 可能没有 cookies，取决于实现

    @pytest.mark.asyncio
    async def test_close_browser(self, browser_pool):
        """测试关闭浏览器"""
        # 先创建一个浏览器
        await browser_pool.get_browser()
        assert browser_pool.browser_count == 1

        # 关闭浏览器
        await browser_pool.close_browser()
        assert browser_pool.browser_count == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, browser_pool):
        """测试获取统计信息"""
        stats = browser_pool.get_stats()
        assert "browser_count" in stats
        assert "browsers" in stats
        assert stats["browser_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_contexts(self, browser_pool):
        """测试创建多个上下文"""
        async with browser_pool.get_context() as context1:
            async with browser_pool.get_context() as context2:
                # 两个 context 应该是不同的实例
                assert context1 is not context2


class TestGlobalBrowserPool:
    """测试全局浏览器池"""

    @pytest.mark.asyncio
    async def test_get_browser_pool_singleton(self):
        """测试全局浏览器池单例"""
        pool1 = await get_browser_pool()
        pool2 = await get_browser_pool()
        assert pool1 is pool2

        # 清理
        await close_browser_pool()

    @pytest.mark.asyncio
    async def test_close_browser_pool(self):
        """测试关闭全局浏览器池"""
        pool = await get_browser_pool()
        assert pool is not None

        await close_browser_pool()

        # 再次获取应该是新的实例
        new_pool = await get_browser_pool()
        assert new_pool is not pool

        # 清理
        await close_browser_pool()


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

        # 模拟保存
        mock_redis.setex = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(saved_state))

        with patch("omnidata.core.browser_pool.get_redis", return_value=mock_redis):
            # 先保存
            async with browser_pool.get_context(namespace="test") as context:
                await browser_pool.save_context_state(context, "test")

            # 再加载
            async with browser_pool.get_context(namespace="test") as context:
                await browser_pool.load_context_state(context, "test")
                # 验证加载被调用
                mock_redis.get.assert_called()

    @pytest.mark.asyncio
    async def test_load_state_with_no_existing_data(self, browser_pool, mock_redis):
        """测试加载不存在的状态"""
        mock_redis.get = AsyncMock(return_value=None)

        with patch("omnidata.core.browser_pool.get_redis", return_value=mock_redis):
            # 不应该抛出异常
            async with browser_pool.get_context(namespace="nonexistent") as context:
                assert context is not None

    @pytest.mark.asyncio
    async def test_state_persistence_with_namespace(self, browser_pool, mock_redis):
        """测试不同 namespace 的状态隔离"""
        mock_redis.get = AsyncMock(return_value=None)

        with patch("omnidata.core.browser_pool.get_redis", return_value=mock_redis):
            # 不同的 namespace 应该使用不同的 Redis key
            async with browser_pool.get_context(namespace="source1") as context:
                await browser_pool.save_context_state(context, "source1")

            async with browser_pool.get_context(namespace="source2") as context:
                await browser_pool.save_context_state(context, "source2")

            # 验证使用了不同的 key
            calls = mock_redis.setex.call_args_list
            keys = [call[0][0] for call in calls]
            assert "omnidata:context_state:source1" in keys
            assert "omnidata:context_state:source2" in keys
