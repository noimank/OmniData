"""
Browser Context Pool 模块
单 Browser + 多 Context 架构，实现 Context 池化管理和状态持久化
"""

import asyncio
import json
import logging
import time
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from omnidata.core.config import BrowserConfig, settings
from omnidata.core.exceptions import BrowserPoolError
from omnidata.utils.redis_client import get_redis
from omnidata.utils.anti_detection_scripts import get_anti_scripts_by_names
logger = logging.getLogger(__name__)


@dataclass
class ContextMetadata:
    """
    Context 元数据包装类

    Attributes:
        context: Playwright BrowserContext 实例
        namespace: 命名空间（用于状态持久化）
        created_at: 创建时间戳
        last_used_at: 最后使用时间戳（用于 LRU）
    """

    context: BrowserContext
    namespace: str | None
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)


class BrowserContextPool:
    """
    单 Browser + 多 Context 池化管理

    功能特性：
    - 单 Browser 实例（无健康检查、无扩缩容）
    - Context 池化（LRU 缓存复用）
    - Context 永不关闭（仅淘汰时关闭）
    - Redis 状态持久化（显式保存，创建时加载）
    - 后台清理任务（闲置回收）
    - Page 自动关闭

    用法示例：
        pool = BrowserContextPool()
        await pool.initialize()

        # 获取 context（复用或创建）
        context = await pool.get_context("test_namespace")

        # 使用 new_page 自动管理 Page 生命周期
        async with pool.new_page("test_namespace") as page:
            await page.goto("https://example.com")

        # 显式保存状态（如登录成功）
        await pool.save_context_state(context, "test_namespace")
    """

    def __init__(self, config: BrowserConfig | None = None):
        """
        初始化 Browser Context 池

        Args:
            config: 浏览器配置
        """
        self._config = config or settings.browser
        self._playwright: Any = None
        self._browser: Browser | None = None
        self._contexts: OrderedDict[str, ContextMetadata] = OrderedDict()
        self._lock = asyncio.Lock()
        self._is_initialized = False
        self._shutdown_event = asyncio.Event()

        # Context Pool 配置
        self._max_pool_size = getattr(self._config, "context_pool_max_size", 10)
        self._idle_timeout = getattr(self._config, "context_idle_timeout", 300)

        # 统计信息
        self._stats = {
            "total_contexts_created": 0,
            "total_contexts_reused": 0,
            "total_contexts_evicted": 0,
            "total_contexts_closed": 0,
        }

        # 后台清理任务
        self._cleanup_task: asyncio.Task[None] | None = None

    async def initialize(self) -> None:
        """初始化 Browser 和清理任务"""
        if self._is_initialized:
            return

        logger.info("Initializing browser context pool...")
        self._playwright = await async_playwright().start()

        launch_options = {
            "headless": self._config.headless,
            "args": self._config.args,
            "ignore_default_args": self._config.ignore_default_args,
        }
        self._browser = await self._playwright.chromium.launch(**launch_options)
        self._is_initialized = True
        self._shutdown_event.clear()

        # 启动后台清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info(
            f"Browser context pool initialized with single chromium browser "
            f"(max_contexts={self._max_pool_size}, idle_timeout={self._idle_timeout}s)"
        )

    async def shutdown(self) -> None:
        """关闭所有 Contexts 和 Browser"""
        if not self._is_initialized:
            return

        logger.info("Shutting down browser context pool...")
        self._is_initialized = False
        self._shutdown_event.set()

        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

        # 关闭所有 context
        async with self._lock:
            for metadata in list(self._contexts.values()):
                await self._close_context(metadata.context)
            self._contexts.clear()

        # 关闭 browser 和 playwright
        await self._close_resource(self._browser, "Browser", "close")
        self._browser = None
        await self._close_resource(self._playwright, "Playwright", "stop")
        self._playwright = None

        logger.info("Browser context pool shut down")

    async def _close_resource(self, resource: Any, name: str, close_method: str = "close") -> None:
        """
        安全关闭资源的辅助方法

        Args:
            resource: 要关闭的资源
            name: 资源名称（用于日志）
            close_method: 关闭方法名，默认为 "close"，playwright 使用 "stop"
        """
        if resource is None:
            return
        try:
            close_func = getattr(resource, close_method)
            await close_func()
            logger.debug(f"{name} closed")
        except asyncio.CancelledError:
            logger.debug(f"{name} close cancelled during shutdown")
        except Exception as e:
            logger.warning(f"Error closing {name.lower()}: {e}")

    async def get_context(self, namespace: str | None = None, **kwargs: Any) -> BrowserContext:
        """
        获取或创建 Context（LRU 复用）

        Args:
            namespace: 命名空间（用于复用和状态持久化）
            **kwargs: 创建 context 时的额外参数

        Returns:
            BrowserContext: 浏览器上下文

        Raises:
            BrowserPoolError: Context 创建失败
        """
        if not self._is_initialized:
            await self.initialize()

        if self._browser is None:
            raise BrowserPoolError("Browser not initialized")

        # 生成 key（使用 namespace 或生成唯一临时 key）
        key = namespace if namespace else f"_temp_{uuid.uuid4().hex[:12]}"

        async with self._lock:
            # 尝试从池中获取
            if key in self._contexts:
                metadata = self._contexts[key]
                if self._is_context_healthy(metadata.context):
                    # 更新 LRU
                    metadata.last_used_at = time.time()
                    self._contexts.move_to_end(key)
                    self._stats["total_contexts_reused"] += 1
                    logger.debug(f"Context reused: namespace={namespace}")
                    return metadata.context
                else:
                    # Context 不健康，移除
                    await self._close_context(metadata.context)
                    del self._contexts[key]

            # 池已满，淘汰最久未使用的
            if len(self._contexts) >= self._max_pool_size:
                await self._evict_lru()

            # 创建新 context
            context = await self._create_context(namespace, **kwargs)
            metadata = ContextMetadata(
                context=context,
                namespace=namespace,
            )
            self._contexts[key] = metadata
            self._stats["total_contexts_created"] += 1
            logger.debug(f"Context created: namespace={namespace}")
            return context

    @asynccontextmanager
    async def new_page(self, namespace: str | None = None, anti_crawling_strategy: str | list="advanced") -> AsyncIterator[Page]:
        """
        创建新 Page（自动关闭）

        Context 不会被关闭，只有 Page 会在退出时自动关闭。

        Args:
            namespace: 命名空间（用于复用和状态持久化）
            anti_crawling_strategy: 反检测脚本策略，支持预设(basic/standard/advanced)
                或单个脚本名称或名称列表。
                预设: basic(基础), standard(标准), advanced(高级)
                单个脚本: navigator_webdriver, chrome_runtime, permissions_query,
                          navigator_languages, webdriver_data, playwright_stealth

        Yields:
            Page: Playwright Page 实例
        """
        context = await self.get_context(namespace)
        page = await context.new_page()
        if anti_crawling_strategy:
            scripts = get_anti_scripts_by_names(anti_crawling_strategy)
            for script in scripts:
                try:
                    await script.apply(page)
                except Exception as e:
                    logger.warning(f"Failed to apply anti-detection script {script.name}: {e}")

        try:
            yield page
        finally:
            # 自动关闭 page，context 不关闭
            if not page.is_closed():
                await page.close()


    async def save_context_state(self, context: BrowserContext, namespace: str) -> None:
        """
        保存状态到 Redis（永久持久化，无 TTL）

        Args:
            context: 浏览器上下文
            namespace: 命名空间
        """
        if not namespace:
            logger.warning("Cannot save context state: namespace is empty")
            return

        try:
            redis = await get_redis()
            key = f"omnidata:context_state:{namespace}"
            state = await context.storage_state()
            await redis.set(key, json.dumps(state))
            logger.debug(f"Context state saved: namespace={namespace} (persistent, no TTL)")
        except Exception as e:
            logger.error(f"Failed to save context state for {namespace}: {e}")

    async def remove_context(self, namespace: str) -> None:
        """
        从池中移除指定 Context

        Args:
            namespace: 命名空间
        """
        if not self._is_initialized:
            return

        async with self._lock:
            if namespace in self._contexts:
                metadata = self._contexts.pop(namespace)
                await self._close_context(metadata.context)
                logger.debug(f"Context removed: namespace={namespace}")

    @property
    def browser(self) -> Browser:
        """获取 Browser 实例"""
        if self._browser is None:
            raise BrowserPoolError("Browser not initialized")
        return self._browser

    @property
    def context_count(self) -> int:
        """获取当前 Context 数量"""
        return len(self._contexts)

    @property
    def is_initialized(self) -> bool:
        """获取初始化状态"""
        return self._is_initialized

    def get_stats(self) -> dict[str, Any]:
        """获取池统计信息"""
        reuse_rate = (
            self._stats["total_contexts_reused"]
            / max(1, self._stats["total_contexts_created"] + self._stats["total_contexts_reused"])
        )

        return {
            "browser_count": 1 if self._browser else 0,
            "context_count": len(self._contexts),
            "total_contexts_created": self._stats["total_contexts_created"],
            "total_contexts_reused": self._stats["total_contexts_reused"],
            "reuse_rate": round(reuse_rate, 4),
            "total_contexts_evicted": self._stats["total_contexts_evicted"],
            "total_contexts_closed": self._stats["total_contexts_closed"],
            "config": {
                "max_pool_size": self._max_pool_size,
                "idle_timeout": self._idle_timeout,
                "headless": self._config.headless,
            },
        }

    async def _create_context(self, namespace: str | None = None, **kwargs: Any) -> BrowserContext:
        """
        创建新的 BrowserContext

        如果有 namespace，从 Redis 加载保存的状态。
        """
        if self._browser is None:
            raise BrowserPoolError("Browser not initialized")

        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            **kwargs
        }

        context = await self._browser.new_context(**context_options)
        context.set_default_timeout(self._config.default_timeout)

        # 仅在创建时加载状态（显式保存）
        if namespace:
            await self._load_context_state(context, namespace)

        return context

    async def _load_context_state(self, context: BrowserContext, namespace: str) -> None:
        """从 Redis 加载 context 状态"""
        try:
            redis = await get_redis()
            key = f"omnidata:context_state:{namespace}"
            data = await redis.get(key)

            if data:
                state = json.loads(data)
                cookies = state.get("cookies", [])
                if cookies:
                    await context.add_cookies(cookies)
                logger.debug(f"Context state loaded: namespace={namespace}")
        except Exception as e:
            logger.error(f"Failed to load context state for {namespace}: {e}")

    async def _close_context(self, context: BrowserContext) -> None:
        """
        关闭 context

        根据 Playwright 最佳实践：
        1. 先关闭所有 pages
        2. 再关闭 context
        """
        try:
            # 先关闭 context 中的所有 pages
            for page in context.pages:
                try:
                    if not page.is_closed():
                        await page.close()
                except Exception:
                    pass

            # 再关闭 context
            await context.close()
            self._stats["total_contexts_closed"] += 1
        except Exception as e:
            logger.debug(f"Error closing context: {e}")

    def _is_context_healthy(self, context: BrowserContext) -> bool:
        """
        检查 context 是否健康

        根据 Playwright 最佳实践：
        1. 通过访问 pages 属性来判断 context 是否可用
        2. 检查 pages 数量是否异常
        """
        try:
            # 检查 pages 数量是否异常（>50 视为异常）
            pages = context.pages
            open_pages = [p for p in pages if not p.is_closed()]
            if len(open_pages) > 50:
                logger.warning(f"Context has too many open pages: {len(open_pages)}")
                return False

            # 尝试访问 browser 来确认 context 仍然连接
            _ = context.browser
            return True

        except Exception as e:
            # 访问属性失败，说明 context 已关闭或不可用
            logger.debug(f"Context health check failed: {e}")
            return False

    async def _evict_lru(self) -> None:
        """
        淘汰最久未使用的 Context

        移除 is_checked_out 机制后，LRU 淘汰逻辑更简单：
        - OrderedDict 第一个元素即最久未使用
        - 即使误淘汰活跃 context，下次 get_context 会重建并从 Redis 恢复状态
        """
        if not self._contexts:
            return

        # 直接淘汰最久未使用的（OrderedDict 第一个元素）
        key, metadata = next(iter(self._contexts.items()))
        await self._close_context(metadata.context)
        del self._contexts[key]
        self._stats["total_contexts_evicted"] += 1
        logger.debug(f"Context evicted (LRU): namespace={metadata.namespace}")

    async def _cleanup_loop(self) -> None:
        """后台清理循环"""
        while self._is_initialized and not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                if self._shutdown_event.is_set():
                    break

                await self._cleanup_idle_contexts()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_idle_contexts(self) -> None:
        """清理闲置 Contexts（超过 idle_timeout）"""
        current_time = time.time()
        keys_to_remove = []

        async with self._lock:
            for key, metadata in self._contexts.items():
                # 检查空闲时间（基于 last_used_at）
                idle_time = current_time - metadata.last_used_at
                if idle_time > self._idle_timeout:
                    keys_to_remove.append(key)
                    logger.debug(
                        f"Context idle timeout: namespace={metadata.namespace}, "
                        f"idle_time={idle_time:.1f}s"
                    )

            # 移除待清理的 context
            for key in keys_to_remove:
                metadata = self._contexts.pop(key)
                await self._close_context(metadata.context)
                logger.debug(f"Context cleaned up: namespace={metadata.namespace}")


# 全局实例
_pool: BrowserContextPool | None = None


def get_browser_context_pool() -> BrowserContextPool:
    """
    获取全局 BrowserContextPool 实例（同步，无锁）

    Returns:
        BrowserContextPool: 浏览器上下文池实例

    Raises:
        BrowserPoolError: 未初始化
    """
    global _pool
    if _pool is None:
        raise BrowserPoolError(
            "BrowserContextPool not initialized. "
            "Ensure main.py lifespan startup completes before calling this function."
        )
    return _pool


def set_browser_context_pool(instance: BrowserContextPool) -> None:
    """
    设置全局 BrowserContextPool 实例（由 main.py lifespan 调用）

    Args:
        instance: 浏览器上下文池实例
    """
    global _pool
    _pool = instance


async def close_browser_context_pool() -> None:
    """关闭全局 BrowserContextPool 实例"""
    global _pool

    if _pool is not None:
        await _pool.shutdown()
        _pool = None
