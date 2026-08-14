"""
测试浏览器上下文池模块
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from playwright.async_api import async_playwright as _async_playwright

from omnidata.core.browser_context_pool import (
    BrowserContextPool,
    close_browser_context_pool,
    get_browser_context_pool,
)
from omnidata.core.config import BrowserConfig
from omnidata.core.exceptions import BrowserPoolError


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

        with patch("omnidata.core.browser_context_pool.get_redis", return_value=mock_redis):
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


class TestIdleTrackingAndRecycle:
    """测试空闲计时与浏览器回收机制（7×24 稳定性核心，内部固定策略）"""

    @pytest.mark.asyncio
    async def test_last_used_at_refreshed_on_reuse(self):
        """复用必须刷新 last_used_at，否则空闲清理会误杀活跃 context"""
        pool = BrowserContextPool(BrowserConfig(headless=True))
        await pool.initialize()
        try:
            context = await pool.get_context(namespace="active_ns")
            metadata = pool._contexts["active_ns"]
            metadata.last_used_at = time.time() - 7200  # 模拟创建已久

            # 复用后 last_used_at 应被刷新
            context_again = await pool.get_context(namespace="active_ns")
            assert context_again is context
            assert time.time() - metadata.last_used_at < 60
        finally:
            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_idle_cleanup_closes_stale_context(self, browser_pool):
        """空闲超时的 context 应被清理"""
        context = await browser_pool.get_context(namespace="stale")
        metadata = browser_pool._contexts["stale"]
        metadata.last_used_at = time.time() - (BrowserContextPool._IDLE_TIMEOUT + 10)

        await browser_pool._cleanup_idle_contexts()

        assert browser_pool.context_count == 0
        assert not context.pages  # context 已关闭

    @pytest.mark.asyncio
    async def test_idle_cleanup_keeps_active_context(self, browser_pool):
        """复用刷新 last_used_at 后，活跃 context 不应被空闲清理误杀"""
        context = await browser_pool.get_context(namespace="active")
        metadata = browser_pool._contexts["active"]
        metadata.created_at = time.time() - 7200  # 创建已久
        metadata.last_used_at = time.time() - 7200

        # 复用一次（应刷新 last_used_at）
        await browser_pool.get_context(namespace="active")

        await browser_pool._cleanup_idle_contexts()
        assert browser_pool.context_count == 1
        assert browser_pool._contexts["active"].context is context

    @pytest.mark.asyncio
    async def test_lru_eviction_removed_no_capacity_limit(self, browser_pool):
        """无容量限制：命名空间数量由数据源决定，context 只由空闲清理回收"""
        for i in range(20):
            await browser_pool.get_context(namespace=f"ns_{i}")

        assert browser_pool.context_count == 20  # 不淘汰，全部保留

    @pytest.mark.asyncio
    async def test_browser_crash_self_heal(self, browser_pool):
        """浏览器崩溃（断连）后应自动重启并继续服务"""
        await browser_pool.get_context(namespace="pre_crash")
        dead_browser = browser_pool._browser
        await dead_browser.close()  # 模拟崩溃

        context = await browser_pool.get_context(namespace="post_crash")

        assert context is not None
        assert browser_pool._browser is not dead_browser
        assert browser_pool.get_stats()["total_browser_recoveries"] == 1
        # 崩溃前的旧 context 随旧 browser 一并清理
        assert browser_pool.get_stats()["context_count"] == 1

    @pytest.mark.asyncio
    async def test_new_page_counters(self, browser_pool):
        """new_page 应维护 active_pages 与 pages_since_recycle 计数"""
        async with browser_pool.new_page():
            assert browser_pool._active_pages == 1
        assert browser_pool._active_pages == 0
        assert browser_pool._pages_since_recycle == 1

    @pytest.mark.asyncio
    async def test_new_page_closed_on_exception(self, browser_pool):
        """异常路径下 page 也必须关闭，计数必须归零"""
        with pytest.raises(RuntimeError):
            async with browser_pool.new_page() as page:
                raise RuntimeError("boom")
        assert page.is_closed()
        assert browser_pool._active_pages == 0

    @pytest.mark.asyncio
    async def test_recycle_replaces_browser(self, browser_pool):
        """回收应替换 browser 实例、清空 context 并更新统计"""
        await browser_pool.get_context(namespace="pre_recycle")
        old_browser = browser_pool._browser
        browser_pool._pages_since_recycle = 123

        await browser_pool._do_recycle()
        stats = browser_pool.get_stats()

        assert browser_pool._browser is not old_browser
        assert browser_pool.context_count == 0
        assert browser_pool._pages_since_recycle == 0
        assert stats["total_browser_recycles"] == 1

        # 回收后可正常获取新 context
        context = await browser_pool.get_context(namespace="post_recycle")
        assert context is not None

    @pytest.mark.asyncio
    async def test_should_recycle_now_waits_for_idle_window(self, browser_pool):
        """达到回收条件但有在途请求时应等待空闲窗口；超过硬上限则强制回收"""
        async with browser_pool.new_page():
            # 满足建页数条件，但有活跃 page → 等待
            browser_pool._pages_since_recycle = BrowserContextPool._RECYCLE_MAX_PAGES
            browser_pool._last_recycle_at = time.time() - 100
            assert not browser_pool._should_recycle_now()

            # 超过硬上限 → 无视在途请求强制回收
            browser_pool._last_recycle_at = time.time() - (
                BrowserContextPool._RECYCLE_HARD_LIMIT + 1
            )
            assert browser_pool._should_recycle_now()

    @pytest.mark.asyncio
    async def test_should_recycle_now_triggers_on_idle(self, browser_pool):
        """达到回收条件且无在途请求时立即回收"""
        browser_pool._pages_since_recycle = BrowserContextPool._RECYCLE_MAX_PAGES
        assert browser_pool._should_recycle_now()

        browser_pool._pages_since_recycle = 0
        browser_pool._last_recycle_at = time.time() - (BrowserContextPool._RECYCLE_MAX_AGE + 1)
        assert browser_pool._should_recycle_now()

    @pytest.mark.asyncio
    async def test_concurrent_initialize_launches_single_browser(self):
        """并发 initialize 不应启动多个 browser"""
        pool = BrowserContextPool(BrowserConfig(headless=True))
        try:
            await asyncio.gather(pool.initialize(), pool.initialize(), pool.initialize())
            assert pool._is_initialized is True
            assert pool._maintenance_task is not None  # 维护任务已创建
        finally:
            await pool.shutdown()


class TestProductionStabilityGuards:
    """生产 7×24 稳定性守护：竞态窗口与自愈盲区"""

    @pytest.mark.asyncio
    async def test_recycle_during_context_creation_discards_stale(self, browser_pool):
        """创建期间浏览器被回收时，过期 context 不得进入缓存（否则该命名空间永久失败）"""
        original_create = browser_pool._create_context
        raced = False

        async def racing_create(browser, namespace=None, **kwargs):
            nonlocal raced
            context = await original_create(browser, namespace, **kwargs)
            if not raced:
                raced = True
                await browser_pool._do_recycle()  # 模拟创建期间发生整体回收
            return context

        browser_pool._create_context = racing_create

        context = await browser_pool.get_context(namespace="racy")

        # 返回的必须是回收后新浏览器上的可用 context，且缓存与之一致
        page = await context.new_page()
        await page.close()
        assert browser_pool._contexts["racy"].context is context
        # 被丢弃的过期 context 不计入创建统计
        stats = browser_pool.get_stats()
        assert stats["total_contexts_created"] == 1
        assert stats["total_browser_recycles"] == 1

    @pytest.mark.asyncio
    async def test_new_page_creation_failure_restores_counter(self, browser_pool):
        """page 创建失败必须归还占位计数，否则回收判定永久误判为忙碌"""

        async def failing_new_page():
            raise RuntimeError("Target page, browser or browser context has been closed")

        context = await browser_pool.get_context(namespace="boom")
        original_new_page = context.new_page
        context.new_page = failing_new_page
        try:
            with pytest.raises(RuntimeError):
                async with browser_pool.new_page(namespace="boom"):
                    pass
        finally:
            context.new_page = original_new_page

        assert browser_pool._active_pages == 0
        assert browser_pool._pages_since_recycle == 0

    @pytest.mark.asyncio
    async def test_get_context_after_shutdown_raises(self):
        """shutdown 后并发到达的请求不得重新拉起浏览器（孤儿进程）"""
        pool = BrowserContextPool(BrowserConfig(headless=True))
        await pool.initialize()
        await pool.shutdown()

        with pytest.raises(BrowserPoolError):
            await pool.get_context(namespace="revive")

    @pytest.mark.asyncio
    async def test_relaunch_rebuilds_dead_playwright_driver(self, browser_pool):
        """launch 失败（驱动死亡）时应整体重建 playwright 驱动并恢复服务"""
        original_playwright = browser_pool._playwright

        class DeadDriver:
            class Chromium:
                async def launch(self, **kwargs):
                    raise RuntimeError("Playwright connection closed")

            chromium = Chromium()

            async def stop(self):
                pass

        class FreshDriverFactory:
            @staticmethod
            async def start():
                return await _async_playwright().start()

        with patch(
            "omnidata.core.browser_context_pool.async_playwright",
            return_value=FreshDriverFactory(),
        ):
            browser_pool._playwright = DeadDriver()
            async with browser_pool._lock:
                await browser_pool._relaunch_browser()

        assert browser_pool._playwright is not original_playwright
        assert browser_pool._browser is not None
        assert browser_pool._browser.is_connected()
        context = await browser_pool.get_context(namespace="after_driver_rebuild")
        page = await context.new_page()
        await page.close()

        await original_playwright.stop()  # 清理测试中换下的旧驱动

    @pytest.mark.asyncio
    async def test_user_agent_follows_browser_version(self, browser_pool):
        """UA 必须跟随实际 Chromium 版本，避免硬编码版本成为指纹破绽"""
        major = browser_pool._browser.version.split(".")[0]
        assert f"Chrome/{major}.0.0.0" in browser_pool._user_agent
        assert browser_pool.get_stats()["config"]["user_agent"] == browser_pool._user_agent
