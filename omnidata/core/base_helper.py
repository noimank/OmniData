"""
公共辅助基类模块
提供 BaseWebSpider 和 BaseQRLogin 的公共方法
"""

import json
import logging
from abc import ABC
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page
from omnidata.utils.redis_client import get_redis

from .browser_pool import BrowserPool
from .config import settings
from .exceptions import BrowserPoolError
from omnidata.utils.anti_detection_scripts import get_anti_scripts_by_names
logger = logging.getLogger(__name__)


class BaseHelper(ABC):
    """
    公共辅助基类

    提供浏览器上下文管理、状态存储、反检测等公共方法
    供 BaseWebSpider 和 BaseQRLogin 继承使用
    """

    def __init__(
        self,
        browser_pool: BrowserPool | None = None,
        config: Any | None = None,
    ):
        """
        初始化

        Args:
            browser_pool: 浏览器池实例
            config: 配置对象
        """
        self._browser_pool = browser_pool
        self.config = config

    @property
    def browser_pool(self) -> BrowserPool:
        """获取浏览器池"""
        if self._browser_pool is None:
            raise BrowserPoolError("Browser pool not initialized")
        return self._browser_pool

    async def apply_anti_detection_scripts(
        self,
        page: Page,
        anti_detection_scripts_names: str | list[str] | None = "advanced",
    ) -> None:
        """
        应用反检测脚本到 page

        Args:
            page: Playwright Page 实例
            anti_detection_scripts_names: 反检测脚本名称，支持预设(basic/standard/advanced)
                或单个脚本名称或名称列表。
                预设: basic(基础), standard(标准), advanced(高级)
                单个脚本: navigator_webdriver, chrome_runtime, permissions_query,
                          navigator_languages, webdriver_data, playwright_stealth
        """
        if anti_detection_scripts_names:
            scripts = get_anti_scripts_by_names(anti_detection_scripts_names)
            for script in scripts:
                try:
                    await script.apply(page)
                except Exception as e:
                    logger.warning(f"Failed to apply anti-detection script {script.name}: {e}")

    async def filter_file_load(self, page: Page, file_types: list[str] | None | str = None) -> None:
        """
        过滤特定文件类型的加载，提高爬取性能

        Args:
            page: Playwright Page 实例
            file_types: 要过滤的文件类型列表
                可选值: document, stylesheet, image, media, font, websocket, manifest
                如果为 None，默认过滤 ['image', 'stylesheet', 'font', 'media']
        """
        if file_types is None:
            file_types = ["image", "stylesheet", "font", "media"]

        if isinstance(file_types, str):
            file_types = [file_types]

        async def route_handler(route):
            if route.request.resource_type in file_types:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)
        logger.debug(f"File types filtered: {file_types}")

    async def save_context_state(self, context: BrowserContext, namespace: str) -> None:
        """
        保存 context 状态到 Redis

        Args:
            context: 浏览器上下文
            namespace: 命名空间（数据源标识）
        """

        try:
            redis = await get_redis()
            key = f"omnidata:context_state:{namespace}"

            # 获取完整状态
            state = await context.storage_state()

            # 保存到 Redis（JSON 格式）
            await redis.setex(key, settings.redis.context_state_ttl, json.dumps(state))
            logger.debug(f"Context state saved for namespace: {namespace}")
        except Exception as e:
            logger.error(f"Failed to save context state for {namespace}: {e}")

    async def _load_context_state(self, context: BrowserContext, namespace: str) -> None:
        """
        从 Redis 加载 context 状态

        Args:
            context: 浏览器上下文
            namespace: 命名空间（数据源标识）
        """

        try:
            redis = await get_redis()
            key = f"omnidata:context_state:{namespace}"

            data = await redis.get(key)
            if data:
                state = json.loads(data)
                # 添加 cookies
                cookies = state.get("cookies", [])
                if cookies:
                    await context.add_cookies(cookies)
                logger.debug(f"Context state loaded for namespace: {namespace}")
            else:
                logger.debug(f"No saved state found for namespace: {namespace}")
        except Exception as e:
            logger.error(f"Failed to load context state for {namespace}: {e}")

    async def remove_context_state(self, namespace: str) -> None:
        """
        删除 Redis 中的 context 状态

        Args:
            namespace: 命名空间（数据源标识）
        """
        try:
            redis = await get_redis()
            key = f"omnidata:context_state:{namespace}"
            await redis.delete(key)
            logger.debug(f"Context state removed for namespace: {namespace}")
        except Exception as e:
            logger.error(f"Failed to remove context state for {namespace}: {e}")

    @asynccontextmanager
    async def get_context(
        self,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[BrowserContext]:
        """
        获取浏览器上下文

        Args:
            namespace: 命名空间，用于加载/保存登录状态
            **kwargs: 其他 context 参数（proxy 等）

        Yields:
            BrowserContext: 浏览器上下文
        """
        # 获取浏览器
        browser = await self.browser_pool.get_browser()
        # 创建 context
        context = await self._create_context(browser, **kwargs)

        # 加载保存的状态
        if namespace:
            await self._load_context_state(context, namespace)

        try:
            yield context
        finally:
            await context.close()

    async def _create_context(
        self,
        browser: Browser,
        **kwargs: Any,
    ) -> BrowserContext:
        """创建浏览器上下文"""
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            # 固定ua，防止一些超高级的反爬监测，随机ua可能有危险，如果不满足需求，项目已经安装了from fake_useragent import UserAgent，可以使用这个库
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            **kwargs
        }

        try:
            context = await browser.new_context(**context_options)
            logger.debug("Context created")
            return context
        except Exception as e:
            raise BrowserPoolError(f"Failed to create context: {e}")

    async def get_context_simple(
        self,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> BrowserContext:
        """
        获取浏览器上下文（需手动关闭）

        与 get_context 不同，此方法返回 context 对象，调用者需要手动关闭。

        Args:
            namespace: 命名空间，用于加载/保存登录状态
            **kwargs: 其他 context 参数（proxy 等）

        Returns:
            BrowserContext: 浏览器上下文（需手动关闭）
        """
        browser = await self.browser_pool.get_browser()
        context = await self._create_context(browser, **kwargs)

        if namespace:
            await self._load_context_state(context, namespace)

        return context
