"""
浏览器管理模块
单 Browser + 按命名空间缓存 Context，配合空闲清理与整体回收实现 7×24 自愈
"""

import asyncio
import gc
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from omnidata.core.config import BrowserConfig, settings
from omnidata.core.exceptions import BrowserPoolError
from omnidata.utils.anti_detection_scripts import get_anti_scripts_by_names
from omnidata.utils.redis_client import get_redis

logger = logging.getLogger(__name__)

_UA_TEMPLATE = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"
)


def _build_user_agent(browser_version: str) -> str:
    """按驱动返回的 Chromium 版本生成 UA，避免硬编码版本与实际内核不一致成为指纹破绽"""
    major = browser_version.split(".")[0]
    return _UA_TEMPLATE.format(major=major)


@dataclass
class ContextMetadata:
    """
    Context 缓存条目

    Attributes:
        context: Playwright BrowserContext 实例
        created_at: 创建时间戳
        last_used_at: 最后使用时间戳（空闲清理依据）
    """

    context: BrowserContext
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)


class BrowserContextPool:
    """
    单 Browser + 按命名空间缓存 Context（7×24 内核级稳定）

    设计原则（对用户透明，无需配置）：
    - 每个命名空间（数据源）持有一个常驻 Context 复用；命名空间数量由
      数据源目录天然决定，无需容量限制
    - Context 空闲 10 分钟自动回收，内存不累积
    - 浏览器整体回收：存活满 8 小时或累计建页满 5000 次（任一先到）时，
      在空闲窗口（无在途请求）关闭全部 context + browser + playwright 驱动并
      整体换新（驱动 Node 进程内存只涨不落，须连进程一起回收），根治长跑
      内存增长；连续 16 小时无空闲窗口才强制执行
    - 自愈覆盖两层：浏览器崩溃（断连）重启 browser；launch 失败视为 playwright
      驱动死亡，整体重建驱动后重试。锁外创建的 context 若遇回收/自愈会被
      丢弃重建，死 context 绝不进入缓存
    - shutdown 后拒绝复活（并发请求不会重新拉起浏览器留下孤儿进程）
    - 登录态持久化于 Redis，回收/重启后自动恢复，对上层无感
    """

    # 内核稳定策略常量（固定值，不对外配置）
    _IDLE_TIMEOUT = 600  # Context 空闲回收阈值（秒）
    _RECYCLE_MAX_AGE = 8 * 3600  # 浏览器最长存活（秒），与建页数任一先到即待回收
    _RECYCLE_MAX_PAGES = 5000  # 两次回收之间累计建页数上限
    _RECYCLE_HARD_LIMIT = _RECYCLE_MAX_AGE * 2  # 连续无空闲超过此时长则强制回收

    def __init__(self, config: BrowserConfig | None = None):
        """
        初始化浏览器管理器

        Args:
            config: 浏览器配置
        """
        self._config = config or settings.browser
        self._playwright: Any = None
        self._browser: Browser | None = None
        self._launch_options: dict[str, Any] = {}
        self._contexts: dict[str, ContextMetadata] = {}
        self._lock = asyncio.Lock()
        self._is_initialized = False
        self._closing = False  # shutdown 后拒绝复活，防止并发请求重新拉起浏览器
        self._shutdown_event = asyncio.Event()
        self._user_agent = _build_user_agent("143")

        # 活跃 Page 计数与回收状态
        self._active_pages = 0
        self._pages_since_recycle = 0
        self._last_recycle_at = time.time()

        # 统计信息
        self._stats = {
            "total_contexts_created": 0,
            "total_contexts_reused": 0,
            "total_contexts_closed": 0,
            "total_browser_recycles": 0,
            "total_browser_recoveries": 0,
        }

        # 后台维护任务（空闲清理 + 回收判定）
        self._maintenance_task: asyncio.Task[None] | None = None

    async def initialize(self) -> None:
        """初始化 Browser 和维护任务（双重检查，防并发重复启动）"""
        if self._is_initialized:
            return

        async with self._lock:
            if self._is_initialized:
                return
            if self._closing:
                raise BrowserPoolError("Browser pool is shut down and cannot be re-initialized")

            logger.info("Initializing browser context pool...")
            # 复用已启动的驱动：launch 失败后重试 initialize 不会泄漏驱动进程
            if self._playwright is None:
                self._playwright = await async_playwright().start()

            self._launch_options = {
                "headless": self._config.headless,
                "args": self._config.args,
                "ignore_default_args": self._config.ignore_default_args,
            }
            await self._launch_browser()
            self._is_initialized = True
            self._last_recycle_at = time.time()
            self._pages_since_recycle = 0
            self._shutdown_event.clear()

            self._maintenance_task = asyncio.create_task(self._maintenance_loop())

            logger.info(
                f"Browser context pool initialized with single chromium browser "
                f"(idle_timeout={self._IDLE_TIMEOUT}s, recycle: max_age={self._RECYCLE_MAX_AGE}s, "
                f"max_pages={self._RECYCLE_MAX_PAGES})"
            )

    async def shutdown(self) -> None:
        """关闭所有 Contexts 和 Browser（关闭后拒绝复活）"""
        if self._closing:
            return

        logger.info("Shutting down browser context pool...")
        self._closing = True
        self._is_initialized = False
        self._shutdown_event.set()

        # 取消维护任务
        if self._maintenance_task:
            self._maintenance_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._maintenance_task
            self._maintenance_task = None

        # 关闭所有 context 和 browser
        async with self._lock:
            await self._close_all_contexts()

        await self._close_resource(self._browser, "Browser", "close")
        self._browser = None
        await self._close_resource(self._playwright, "Playwright driver", "stop")
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
        获取或创建指定命名空间的 Context（复用缓存）

        慢速的 context 创建操作移出锁外，减少锁竞争。创建期间若浏览器被
        回收/自愈（Browser 实例被替换），锁外创建的 Context 已随旧浏览器
        关闭，必须丢弃重建——否则缓存死 Context 会导致该命名空间永久失败。

        Args:
            namespace: 命名空间（用于复用和状态持久化）
            **kwargs: 创建 context 时的额外参数

        Returns:
            BrowserContext: 浏览器上下文

        Raises:
            BrowserPoolError: Context 创建失败，或池已关闭
        """
        # 命名空间使用固定 key 复用；临时请求使用唯一 key（由空闲清理兜底回收）
        key = namespace if namespace else f"_temp_{uuid.uuid4().hex[:12]}"

        while True:
            if self._closing:
                raise BrowserPoolError("Browser pool is shut down")
            if not self._is_initialized:
                await self.initialize()

            browser = await self._ensure_browser()

            # === 命中缓存：直接复用 ===
            async with self._lock:
                cached = self._contexts.get(key)
                if cached is not None:
                    cached.last_used_at = time.time()
                    self._stats["total_contexts_reused"] += 1
                    return cached.context

            # === 未命中：锁外创建（含 Redis 状态加载，可能耗时） ===
            context = await self._create_context(browser, namespace, **kwargs)

            # === 插入缓存；并发竞态下保留先创建的，关闭多余的 ===
            stale = False
            duplicate: BrowserContext | None = None
            async with self._lock:
                # 创建期间浏览器被回收/自愈 → context 已随旧浏览器关闭，不可入缓存
                if self._browser is not browser or self._closing:
                    stale = True
                else:
                    cached = self._contexts.get(key)
                    if cached is not None:
                        duplicate = context
                        result_context = cached.context
                        self._stats["total_contexts_reused"] += 1
                    else:
                        self._contexts[key] = ContextMetadata(context=context)
                        self._stats["total_contexts_created"] += 1
                        result_context = context

            if stale:
                await self._close_context(context)
                continue  # 浏览器已更换，重新获取并在新浏览器上重建
            if duplicate is not None:
                await self._close_context(duplicate)

            return result_context

    @asynccontextmanager
    async def new_page(
        self, namespace: str | None = None, anti_crawling_strategy: str | list = "advanced"
    ) -> AsyncIterator[Page]:
        """
        创建新 Page（自动关闭，维护活跃计数）

        Context 不会被关闭，只有 Page 会在退出时自动关闭。
        活跃 Page 计数用于驱动浏览器在空闲窗口安全回收。

        Args:
            namespace: 命名空间（用于复用和状态持久化）
            anti_crawling_strategy: 反检测脚本策略，支持预设(basic/standard/advanced)
                或单个脚本名称或名称列表。

        Yields:
            Page: Playwright Page 实例
        """
        context = await self.get_context(namespace)
        # 创建前先占位：否则 await new_page() 期间计数为 0，
        # 回收判定会把创建中的 page 误判为空闲窗口而将其关闭
        self._active_pages += 1
        try:
            page = await context.new_page()
        except Exception:
            self._active_pages -= 1
            raise
        self._pages_since_recycle += 1

        try:
            if anti_crawling_strategy:
                scripts = get_anti_scripts_by_names(anti_crawling_strategy)
                for script in scripts:
                    try:
                        await script.apply(page)
                    except Exception as e:
                        logger.warning(f"Failed to apply anti-detection script {script.name}: {e}")
            yield page
        finally:
            self._active_pages -= 1
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
        从缓存中移除指定命名空间的 Context（锁内移除，锁外关闭）

        Args:
            namespace: 命名空间
        """
        if not self._is_initialized:
            return

        async with self._lock:
            metadata = self._contexts.pop(namespace, None)

        if metadata is not None:
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
        """获取统计信息"""
        reuse_rate = self._stats["total_contexts_reused"] / max(
            1, self._stats["total_contexts_created"] + self._stats["total_contexts_reused"]
        )

        return {
            "browser_count": 1 if self._browser else 0,
            "context_count": len(self._contexts),
            "active_pages": self._active_pages,
            "total_contexts_created": self._stats["total_contexts_created"],
            "total_contexts_reused": self._stats["total_contexts_reused"],
            "reuse_rate": round(reuse_rate, 4),
            "total_contexts_closed": self._stats["total_contexts_closed"],
            "total_browser_recycles": self._stats["total_browser_recycles"],
            "total_browser_recoveries": self._stats["total_browser_recoveries"],
            "pages_since_recycle": self._pages_since_recycle,
            "last_recycle_at": self._last_recycle_at,
            "config": {
                "idle_timeout": self._IDLE_TIMEOUT,
                "headless": self._config.headless,
                "user_agent": self._user_agent,
            },
        }

    def get_contexts(self) -> list[dict[str, Any]]:
        """
        获取当前所有 Context 的详细信息

        Returns:
            Context 信息列表
        """
        contexts = []
        for key, metadata in self._contexts.items():
            contexts.append(
                {
                    "namespace": key,
                    "key": key,
                    "created_at": metadata.created_at,
                    "last_used_at": metadata.last_used_at,
                    "idle_time": round(time.time() - metadata.last_used_at, 1),
                    "pages_count": len(metadata.context.pages),
                }
            )
        return contexts

    async def _create_context(
        self, browser: Browser, namespace: str | None = None, **kwargs: Any
    ) -> BrowserContext:
        """
        在指定 Browser 上创建新的 BrowserContext

        如果有 namespace，从 Redis 加载保存的状态（cookies + localStorage）。
        使用 Playwright 原生的 storage_state 机制，自动恢复所有状态。
        """
        # 准备 context 选项
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "user_agent": self._user_agent,
            **kwargs,
        }

        # 从 Redis 加载 storage_state
        storage_state = None
        if namespace:
            storage_state = await self._get_storage_state(namespace)
            if storage_state:
                # 使用 storage_state 参数，Playwright 会自动恢复 cookies 和 localStorage
                context_options["storage_state"] = storage_state

        context = await browser.new_context(**context_options)
        context.set_default_timeout(self._config.default_timeout)

        return context

    async def _get_storage_state(self, namespace: str) -> dict | None:
        """
        从 Redis 获取 storage_state（包含 cookies + localStorage）

        Returns:
            storage_state 对象或 None（如果不存在）
        """
        try:
            redis = await get_redis()
            key = f"omnidata:context_state:{namespace}"
            data = await redis.get(key)

            if data:
                state = json.loads(data)

                # 验证数据完整性
                cookies = state.get("cookies", [])
                origins = state.get("origins", [])

                if not cookies and not origins:
                    logger.debug(f"Empty storage state for namespace={namespace}")
                    return None

                logger.debug(
                    f"Storage state loaded: namespace={namespace}, "
                    f"cookies={len(cookies)}, origins={len(origins)}"
                )
                return state

            return None
        except Exception as e:
            logger.error(f"Failed to get storage state for {namespace}: {e}")
            return None

    async def _ensure_browser(self) -> Browser:
        """
        获取当前可用的 Browser 实例，不可用时自动自愈。

        - 回收期间 _browser 短暂为 None（全程持锁），等待锁即可拿到新实例
        - 浏览器崩溃（断连）时重启 browser，实现内核级自愈
        """
        if self._browser is not None and self._browser.is_connected():
            return self._browser

        async with self._lock:
            # 双重检查：等待锁期间其他协程可能已完成重启/回收
            if self._browser is not None and self._browser.is_connected():
                return self._browser
            if self._closing:
                raise BrowserPoolError("Browser pool is shut down")

            logger.warning("Browser unavailable (crashed or failed launch), self-healing relaunch")
            await self._relaunch_browser()
            self._stats["total_browser_recoveries"] += 1
            return self._browser  # launch 失败会抛异常，不会返回 None

    async def _launch_browser(self) -> None:
        """在当前 playwright 驱动上启动 Browser 并刷新 UA 版本（调用方需持有 _lock）"""
        self._browser = await self._playwright.chromium.launch(**self._launch_options)
        self._user_agent = _build_user_agent(self._browser.version)

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

    async def _close_all_contexts(self) -> None:
        """关闭并清空全部缓存 Context（调用方需持有 _lock）"""
        for metadata in list(self._contexts.values()):
            await self._close_context(metadata.context)
        self._contexts.clear()

    async def _rebuild_driver(self) -> None:
        """整体重建 playwright 驱动，换新 Node 进程（调用方需持有 _lock）"""
        await self._close_resource(self._playwright, "Playwright driver", "stop")
        self._playwright = await async_playwright().start()

    async def _relaunch_browser(self, rebuild_driver: bool = False) -> None:
        """
        关闭现有 browser 并重新 launch，重置回收计数（调用方需持有 _lock）。

        全部 context 随旧 browser 一起关闭；登录态会在后续 get_context 时
        从 Redis 自动恢复。
        - rebuild_driver=True：连 playwright 驱动一起换新。Node 驱动长跑后
          内存只涨不落（V8 不向 OS 归还内存），定期回收必须连驱动进程一起
          重建才能根治；此时 launch 仍失败则直接上抛，交由 _ensure_browser
          自愈兜底
        - rebuild_driver=False（崩溃自愈快路径）：launch 失败视为 playwright
          驱动已死亡（长跑进程 OOM/被杀），整体重建驱动后重试一次，堵住
          "驱动死亡后永远无法自愈"的缺口
        """
        await self._close_all_contexts()
        await self._close_resource(self._browser, "Browser", "close")
        self._browser = None

        if rebuild_driver:
            await self._rebuild_driver()

        try:
            await self._launch_browser()
        except Exception as e:
            if rebuild_driver:
                raise  # 驱动刚换新仍失败，交给自愈路径（_ensure_browser）兜底
            logger.warning(f"Browser relaunch failed ({e}), rebuilding playwright driver")
            await self._rebuild_driver()
            await self._launch_browser()
        self._last_recycle_at = time.time()
        self._pages_since_recycle = 0

    async def _cleanup_idle_contexts(self) -> None:
        """清理闲置 Contexts。锁内收集并移除，锁外关闭。"""
        current_time = time.time()
        async with self._lock:
            stale_keys = [
                key
                for key, meta in self._contexts.items()
                if current_time - meta.last_used_at > self._IDLE_TIMEOUT
            ]
            victims = [(key, self._contexts.pop(key)) for key in stale_keys]

        for key, meta in victims:
            await self._close_context(meta.context)
            logger.debug(
                f"Context cleaned up (idle): namespace={key}, "
                f"idle_time={current_time - meta.last_used_at:.1f}s"
            )

    def _should_recycle_now(self) -> bool:
        """
        判断是否应立即执行浏览器回收。

        达到回收条件（存活超时或建页超量），且当前处于可安全回收的时机：
        空闲窗口（无在途请求），或已超过硬上限（不允许再等）。
        """
        age = time.time() - self._last_recycle_at
        if age >= self._RECYCLE_HARD_LIMIT:
            return True
        if age >= self._RECYCLE_MAX_AGE or self._pages_since_recycle >= self._RECYCLE_MAX_PAGES:
            return self._active_pages == 0
        return False

    async def _maintenance_loop(self) -> None:
        """后台维护循环：空闲清理 + 浏览器回收"""
        while self._is_initialized and not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                if self._shutdown_event.is_set():
                    break

                await self._cleanup_idle_contexts()

                if self._should_recycle_now():
                    await self._do_recycle()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance error: {e}")

    async def _do_recycle(self) -> None:
        """
        执行浏览器与 playwright 驱动的整体回收。

        全程持锁（关闭 + 重启通常仅数秒，每数小时一次），确保回收期间
        get_context 阻塞等待而非拿到即将失效的 browser。锁外补一次
        gc.collect()，及时回收旧 browser/驱动在 Python 侧留下的对象图。
        """
        async with self._lock:
            age = time.time() - self._last_recycle_at
            logger.info(
                f"Recycling browser and playwright driver "
                f"(pages_since_recycle={self._pages_since_recycle}, "
                f"age={age:.0f}s, active_pages={self._active_pages})"
            )

            await self._relaunch_browser(rebuild_driver=True)
            self._stats["total_browser_recycles"] += 1
            logger.info("Browser and playwright driver recycled successfully")
        gc.collect()


@lru_cache(maxsize=1)
def get_browser_context_pool() -> BrowserContextPool:
    """
    获取全局 BrowserContextPool 实例（单例）

    Returns:
        BrowserContextPool: 浏览器上下文池实例
    """
    return BrowserContextPool()


async def close_browser_context_pool() -> None:
    """关闭全局 BrowserContextPool 实例并清除缓存"""
    pool = get_browser_context_pool()
    await pool.shutdown()
    get_browser_context_pool.cache_clear()
