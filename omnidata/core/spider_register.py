"""
爬虫注册器模块
自动发现和注册 data_sources 目录下的所有爬虫类
"""

import asyncio
import importlib
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any

from .base_web_spider import BaseWebSpider
from .browser_pool import BrowserPool, get_browser_pool
from .exceptions import SpiderNotFoundError, SpiderRegistrationError

logger = logging.getLogger(__name__)


class SpiderRegister:
    """
    爬虫注册器

    自动发现、加载和管理所有爬虫类
    """

    def __init__(
        self,
        browser_pool: BrowserPool | None = None,
    ):
        """
        初始化爬虫注册器

        Args:
            browser_pool: 浏览器池实例
        """
        self._data_sources_dir = Path(__file__).parent.parent.joinpath("data_sources")
        self._browser_pool = browser_pool
        self._spiders: dict[str, type[BaseWebSpider]] = {}
        self._instances: dict[str, BaseWebSpider] = {}
        self._is_initialized = False

    async def initialize(self) -> None:
        """初始化注册器并自动发现爬虫"""
        if self._is_initialized:
            return

        if self._browser_pool is None:
            self._browser_pool = await get_browser_pool()

        await self._discover_spiders()
        self._is_initialized = True

        logger.info(f"SpiderRegister initialized with {len(self._spiders)} spiders")

    async def shutdown(self) -> None:
        """关闭注册器"""
        self._spiders.clear()
        self._instances.clear()
        self._is_initialized = False
        logger.info("SpiderRegister shut down")

    async def _discover_spiders(self) -> None:
        """自动发现并注册所有爬虫"""
        if not self._data_sources_dir.exists():
            logger.warning(f"Data sources directory not found: {self._data_sources_dir}")
            return

        # 确保目录在 Python 路径中
        dir_str = str(self._data_sources_dir.parent)
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)

        # 遍历所有 Python 文件
        for py_file in self._data_sources_dir.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            await self._load_spiders_from_file(py_file)

    async def _load_spiders_from_file(self, file_path: Path) -> None:
        """
        从文件中加载爬虫类

        Args:
            file_path: Python 文件路径
        """
        try:
            # 构建模块名
            rel_path = file_path.relative_to(self._data_sources_dir.parent)
            module_name = str(rel_path.with_suffix("")).replace(os.sep, ".")

            # 动态导入模块
            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    logger.warning(f"Could not load spec for {file_path}")
                    return
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            # 查找所有 BaseWebSpider 子类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BaseWebSpider)
                    and obj is not BaseWebSpider
                    and obj.__module__ == module_name
                ):
                    self._register_spider_class(obj)

        except Exception as e:
            logger.error(f"Error loading spiders from {file_path}: {e}")

    def _register_spider_class(self, spider_class: type[BaseWebSpider]) -> None:
        """
        注册爬虫类

        Args:
            spider_class: 爬虫类
        """
        spider_name = spider_class.name or spider_class.__name__

        if spider_name in self._spiders:
            logger.warning(f"Spider {spider_name} already registered, skipping")
            return


        self._spiders[spider_name] = spider_class
        logger.info(f"Registered spider: {spider_name}")

    def register_spider(self, spider_class: type[BaseWebSpider]) -> None:
        """
        手动注册爬虫类

        Args:
            spider_class: 爬虫类
        """
        if not issubclass(spider_class, BaseWebSpider):
            raise SpiderRegistrationError(
                f"{spider_class.__name__} must be a subclass of BaseWebSpider"
            )

        self._register_spider_class(spider_class)

    def register_spider_instance(self, spider: BaseWebSpider) -> None:
        """
        注册爬虫实例

        Args:
            spider: 爬虫实例
        """
        spider_name = spider.name or spider.__class__.__name__
        self._instances[spider_name] = spider
        self._spiders[spider_name] = spider.__class__
        logger.info(f"Registered spider instance: {spider_name}")

    def unregister_spider(self, spider_name: str) -> None:
        """
        注销爬虫

        Args:
            spider_name: 爬虫名称
        """
        if spider_name in self._spiders:
            del self._spiders[spider_name]
            logger.info(f"Unregistered spider: {spider_name}")

        if spider_name in self._instances:
            del self._instances[spider_name]

    def get_spider_class(self, spider_name: str) -> type[BaseWebSpider]:
        """
        获取爬虫类

        Args:
            spider_name: 爬虫名称

        Returns:
            爬虫类

        Raises:
            SpiderNotFoundError: 爬虫未找到
        """
        if spider_name not in self._spiders:
            raise SpiderNotFoundError(f"Spider '{spider_name}' not found")
        return self._spiders[spider_name]

    def get_spider_instance(self, spider_name: str) -> BaseWebSpider:
        """
        获取或创建爬虫实例

        Args:
            spider_name: 爬虫名称

        Returns:
            爬虫实例

        Raises:
            SpiderNotFoundError: 爬虫未找到
        """
        if spider_name in self._instances:
            return self._instances[spider_name]

        spider_class = self.get_spider_class(spider_name)

        # 创建实例并注入浏览器池
        instance = spider_class(browser_pool=self._browser_pool)
        self._instances[spider_name] = instance

        return instance

    def list_spiders(self) -> list[str]:
        """
        列出所有已注册的爬虫名称

        Returns:
            爬虫名称列表
        """
        return list(self._spiders.keys())

    def list_spider_info(self) -> list[dict[str, Any]]:
        """
        列出所有爬虫的详细信息

        Returns:
            爬虫信息列表
        """
        return [spider_class.get_info() for spider_class in self._spiders.values()]

    def get_spider_info(self, spider_name: str) -> dict[str, Any]:
        """
        获取爬虫详细信息

        Args:
            spider_name: 爬虫名称

        Returns:
            爬虫信息字典

        Raises:
            SpiderNotFoundError: 爬虫未找到
        """
        spider_class = self.get_spider_class(spider_name)
        return spider_class.get_info()

    async def run_spider(
        self,
        spider_name: str,
        params: dict[str, Any],
    ) -> Any:
        """
        运行指定的爬虫

        Args:
            spider_name: 爬虫名称
            params: 爬虫参数

        Returns:
            爬虫结果

        Raises:
            SpiderNotFoundError: 爬虫未找到
        """
        spider = self.get_spider_instance(spider_name)
        return await spider.run(params)

    async def run_spider_batch(
        self,
        spider_name: str,
        params_list: list[dict[str, Any]],
        max_concurrency: int = 3,
    ) -> list[Any]:
        """
        批量运行指定的爬虫

        Args:
            spider_name: 爬虫名称
            params_list: 参数列表
            max_concurrency: 最大并发数

        Returns:
            结果列表

        Raises:
            SpiderNotFoundError: 爬虫未找到
        """
        spider = self.get_spider_instance(spider_name)
        return await spider.run_batch(params_list, max_concurrency)

    @property
    def spider_count(self) -> int:
        """获取已注册爬虫数量"""
        return len(self._spiders)

    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._is_initialized


# 全局爬虫注册器实例
_spider_register: SpiderRegister | None = None
_register_lock: "asyncio.Lock" = None


async def get_spider_register(
    browser_pool: BrowserPool | None = None,
) -> SpiderRegister:
    """
    获取全局爬虫注册器实例

    Args:
        browser_pool: 浏览器池实例

    Returns:
        SpiderRegister: 爬虫注册器实例
    """
    global _spider_register, _register_lock

    if _register_lock is None:
        _register_lock = asyncio.Lock()

    async with _register_lock:
        if _spider_register is None:
            _spider_register = SpiderRegister(browser_pool)
            await _spider_register.initialize()

        return _spider_register


async def close_spider_register() -> None:
    """关闭全局爬虫注册器"""
    global _spider_register

    if _spider_register is not None:
        await _spider_register.shutdown()
        _spider_register = None


# 便捷访问器（用于非异步上下文）
def spider_register() -> SpiderRegister:
    """
    获取爬虫注册器（非异步版本）

    注意: 使用前需要确保已初始化

    Returns:
        SpiderRegister: 爬虫注册器实例
    """
    global _spider_register

    if _spider_register is None:
        raise SpiderRegistrationError(
            "Spider register not initialized. Use await get_spider_register() first."
        )

    return _spider_register
