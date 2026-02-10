"""
公共辅助基类模块
提供 BaseWebSpider 和 BaseQRLogin 的公共方法
"""

import logging
from abc import ABC
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from playwright.async_api import BrowserContext, Page, Route

from omnidata.utils.anti_detection_scripts import get_anti_scripts_by_names
from omnidata.utils.redis_client import get_redis

from .browser_context_pool import BrowserContextPool
from .exceptions import BrowserPoolError

logger = logging.getLogger(__name__)


class BaseHelper(ABC):
    """
    公共辅助基类

    提供浏览器上下文管理、状态存储、反检测等公共方法
    供 BaseWebSpider 和 BaseQRLogin 继承使用
    """

    def __init__(
        self,
        browser_context_pool: BrowserContextPool | None = None,
        config: Any | None = None,
    ):
        """
        初始化

        Args:
            browser_context_pool: 浏览器上下文池实例
            config: 配置对象
        """
        self._browser_context_pool = browser_context_pool
        self.config = config

    @property
    def browser_context_pool(self) -> BrowserContextPool:
        """获取浏览器上下文池"""
        if self._browser_context_pool is None:
            raise BrowserPoolError("Browser context pool not initialized")
        return self._browser_context_pool

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

        async def route_handler(route: Route) -> None:
            if route.request.resource_type in file_types:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)
        logger.debug(f"File types filtered: {file_types}")

    async def save_context_state(self, context: BrowserContext, namespace: str) -> None:
        """
        保存 context 状态到 Redis

        适用场景：
        - 登录成功后保存登录状态
        - 定期刷新登录状态

        Args:
            context: 浏览器上下文
            namespace: 命名空间（数据源标识）
        """
        await self.browser_context_pool.save_context_state(context, namespace)


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

    async def get_context(
        self,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> BrowserContext:
        """
        获取浏览器上下文（由 ContextPool 自动管理生命周期）

        Context 会被自动复用，ContextPool 会自动处理：
        - LRU 淘汰（池满时）
        - 健康检查（清理不健康的 context）
        - 空闲超时（5分钟未使用自动关闭）
        - 状态加载（从 Redis 自动加载已保存的 cookies）

        ⚠️ 重要：
        - 获取 context 时会自动加载 Redis 中的状态（如果存在）
        - 释放 context 时不会自动保存状态
        - 如需保存状态（如登录成功），请显式调用 save_context_state()

        Args:
            namespace: 命名空间，用于复用和状态持久化
            **kwargs: 其他 context 参数（proxy 等）

        Returns:
            BrowserContext: 浏览器上下文

        Example:
            >>> # 普通爬虫：不需要保存状态
            >>> context = await self.get_context()
            >>> page = await context.new_page()
            >>> await page.goto("https://example.com")

            >>> # 登录器：显式保存状态
            >>> context = await self.get_context(namespace="my_app")
            >>> page = await context.new_page()
            >>> # ... 登录成功后 ...
            >>> await self.save_context_state(context, "my_app")
        """
        return await self.browser_context_pool.get_context(namespace, **kwargs)


    @asynccontextmanager
    async def new_page(
        self,
        namespace: str | None = None,
        anti_crawling_strategy: str | list="advanced",
    ) -> AsyncIterator[Page]:
        """
        创建新页面（自动管理 context 和 page 的生命周期）

        这是对 get_context 的进一步封装，直接返回 Page 对象，
        用户无需手动管理 page 和 context 的关闭。

        Args:
            namespace: 命名空间，用于复用和状态持久化
            anti_crawling_strategy: 反检测脚本策略，支持预设(basic/standard/advanced)
                或单个脚本名称或名称列表。
                预设: basic(基础), standard(标准), advanced(高级)
                单个脚本: navigator_webdriver, chrome_runtime, permissions_query,
                          navigator_languages, webdriver_data, playwright_stealth

        Yields:
            Page: Playwright Page 实例

        Example:
            >>> async with self.new_page(namespace="my_namespace") as page:
            ...     await page.goto("https://example.com")
            ...     title = await page.title()
        """
        # 使用 BrowserContextPool 的 new_page 方法，自动管理 Page 生命周期
        async with self.browser_context_pool.new_page(namespace, anti_crawling_strategy) as page:
            yield page

