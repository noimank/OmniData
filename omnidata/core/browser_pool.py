"""
浏览器池管理模块
基于 Playwright 实现浏览器连接池，支持浏览器实例的复用和管理
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import cycle
from typing import Any

from playwright.async_api import (
    Browser,
    async_playwright,
)

from .config import BrowserConfig, settings
from .exceptions import BrowserPoolError, BrowserTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class BrowserWrapper:
    """浏览器包装类"""

    browser: Browser
    index: int  # 浏览器索引
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)

    @property
    def idle_time(self) -> timedelta:
        """获取空闲时间"""
        return datetime.now() - self.last_used_at

    def mark_used(self) -> None:
        """标记为已使用"""
        self.last_used_at = datetime.now()


class BrowserPool:
    """
    浏览器连接池

    初始化时创建固定数量的浏览器实例，通过轮询方式分配浏览器
    空闲超时后重启浏览器
    """

    def __init__(self, config: BrowserConfig | None = None):
        """
        初始化浏览器池

        Args:
            config: 浏览器配置
        """
        self._config = config or settings.browser
        self._playwright = None
        self._browsers: list[BrowserWrapper] = []
        self._browser_cycle: cycle | None = None
        self._lock = asyncio.Lock()
        self._is_initialized = False
        self._cleanup_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """初始化浏览器池，预创建固定数量的浏览器"""
        if self._is_initialized:
            return

        logger.info("Initializing browser pool...")
        self._playwright = await async_playwright().start()

        # 预创建浏览器
        for i in range(self._config.pool_initial_size):
            await self._create_browser(i)

        # 创建轮询迭代器
        self._browser_cycle = cycle(self._browsers)

        self._is_initialized = True

        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._restart_idle_browsers())

        logger.info(f"Browser pool initialized with {len(self._browsers)} chromium browsers")

    async def shutdown(self) -> None:
        """关闭浏览器池"""
        if not self._is_initialized:
            return

        logger.info("Shutting down browser pool...")

        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 关闭所有浏览器
        async with self._lock:
            for browser_wrapper in self._browsers:
                await self._close_browser(browser_wrapper)
            self._browsers.clear()
            self._browser_cycle = None

        # 关闭 playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except asyncio.CancelledError:
                # 在关闭过程中 CancelledError 是预期的，静默处理
                logger.debug("Playwright stop cancelled during shutdown")
            except Exception as e:
                logger.warning(f"Error stopping playwright: {e}")

        self._is_initialized = False
        logger.info("Browser pool shut down")

    async def get_browser(self) -> Browser:
        """
        获取浏览器实例（轮询方式）

        Returns:
            Browser: 浏览器实例
        """
        if not self._is_initialized:
            await self.initialize()

        async with self._lock:
            if not self._browser_cycle:
                raise BrowserPoolError("Browser pool not initialized")

            browser_wrapper = next(self._browser_cycle)
            browser_wrapper.mark_used()
            return browser_wrapper.browser


    async def _create_browser(self, index: int) -> None:
        """创建浏览器实例"""
        launch_options = {
            "headless": self._config.headless,
            "args": self._config.args,
            "ignore_default_args": self._config.ignore_default_args,
        }

        try:
            browser = await asyncio.wait_for(
                self._playwright.chromium.launch(**launch_options),
                timeout=self._config.launch_timeout,
            )
        except TimeoutError:
            raise BrowserTimeoutError("Browser launch timeout")
        except Exception as e:
            raise BrowserPoolError(f"Failed to launch browser: {e}")

        self._browsers.append(BrowserWrapper(browser=browser, index=index))
        logger.info(f"Browser created: index={index}, total browsers: {len(self._browsers)}")


    async def _close_browser(self, browser_wrapper: BrowserWrapper) -> None:
        """关闭浏览器实例"""
        try:
            await browser_wrapper.browser.close()
            logger.debug(f"Browser closed: index={browser_wrapper.index}")
        except asyncio.CancelledError:
            # 在关闭过程中 CancelledError 是预期的，静默处理
            logger.debug(f"Browser close cancelled: index={browser_wrapper.index}")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def _restart_browser(self, browser_wrapper: BrowserWrapper) -> BrowserWrapper:
        """重启浏览器实例"""
        index = browser_wrapper.index
        await self._close_browser(browser_wrapper)

        launch_options = {
            "headless": self._config.headless,
            "args": self._config.args,
            "ignore_default_args": self._config.ignore_default_args,
        }

        try:
            browser = await asyncio.wait_for(
                self._playwright.chromium.launch(**launch_options),
                timeout=self._config.launch_timeout,
            )
        except TimeoutError:
            raise BrowserTimeoutError("Browser launch timeout")
        except Exception as e:
            raise BrowserPoolError(f"Failed to restart browser: {e}")

        new_wrapper = BrowserWrapper(browser=browser, index=index)
        logger.info(f"Browser restarted: index={index}")
        return new_wrapper

    async def _restart_idle_browsers(self) -> None:
        """定期重启空闲浏览器"""
        while self._is_initialized:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次

                async with self._lock:
                    # 检查需要重启的浏览器
                    for i, browser_wrapper in enumerate(self._browsers):
                        if browser_wrapper.idle_time.total_seconds() > self._config.idle_timeout:
                            logger.info(
                                f"Restarting idle browser: index={browser_wrapper.index}, "
                                f"idle_time={browser_wrapper.idle_time.total_seconds():.0f}s"
                            )
                            self._browsers[i] = await self._restart_browser(browser_wrapper)

                    # 重新创建轮询迭代器
                    self._browser_cycle = cycle(self._browsers)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    @property
    def browser_count(self) -> int:
        """获取当前浏览器数量"""
        return len(self._browsers)

    def get_stats(self) -> dict[str, Any]:
        """获取池统计信息"""
        return {
            "browser_count": self.browser_count,
            "browsers": [
                {
                    "index": bw.index,
                    "idle_time_seconds": bw.idle_time.total_seconds(),
                }
                for bw in self._browsers
            ],
        }


# 全局浏览器池实例
_browser_pool: BrowserPool | None = None
_pool_lock = asyncio.Lock()


async def get_browser_pool(config: BrowserConfig | None = None) -> BrowserPool:
    """
    获取全局浏览器池实例

    Args:
        config: 浏览器配置

    Returns:
        BrowserPool: 浏览器池实例
    """
    global _browser_pool

    async with _pool_lock:
        if _browser_pool is None:
            _browser_pool = BrowserPool(config)
            await _browser_pool.initialize()

        return _browser_pool


async def close_browser_pool() -> None:
    """关闭全局浏览器池"""
    global _browser_pool

    async with _pool_lock:
        if _browser_pool is not None:
            await _browser_pool.shutdown()
            _browser_pool = None
