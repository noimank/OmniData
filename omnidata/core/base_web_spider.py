"""
爬虫基类模块
提供爬虫的通用功能，子类只需实现 crawl 方法
"""

import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .base_helper import BaseHelper
from .browser_pool import BrowserPool
from .exceptions import SpiderError, SpiderValidationError

logger = logging.getLogger(__name__)


@dataclass
class SpiderResult:
    """爬虫执行结果"""

    spider_name: str
    success: bool
    data: dict[str, Any] | list[dict[str, Any]] | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "spider_name": self.spider_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


class BaseWebSpider(BaseHelper):
    """
    爬虫基类

    子类需要实现以下方法:
        - crawl: 具体的爬取逻辑（必需）
        - postprocess: 结果后处理（可选）

    使用示例:
        ```python
        from pydantic import BaseModel, Field
        from omnidata.core.base_web_spider import BaseWebSpider

        class MyParams(BaseModel):
            url: str = Field(..., description="目标URL")
            keyword: str = Field(default="", description="搜索关键词")

        class MySpider(BaseWebSpider):
            name = "my_spider"
            description = "我的爬虫"
            params_model = MyParams
            platform = "我的平台"
            version = "1.0.0"
            author = "我"


            async def crawl(self, params: MyParams) -> dict:
                # 通过 browser_pool.get_context() 获取上下文
                async with self.browser_pool.get_context() as context:
                    page = await context.new_page()
                    try:
                        await page.goto(params.url)
                        title = await page.title()
                        return {"title": title, "url": params.url}
                    finally:
                        await page.close()
        ```

    属性说明:
        - self.config: 爬虫配置对象
        - self.browser_pool: 浏览器池实例

    可用方法:
        - async with self.browser_pool.get_context(namespace="xxx", use_stealth=True): 获取浏览器上下文
        - 用户需自行从 context 创建 page: page = await context.new_page()
    """

    # 爬虫名称，整个系统中需要唯一标识，统一以 数据源+下划线+爬虫名称编码，如 eastmoney_news_query
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    #平台名称，就统一设置为对应数据源的中文名称
    platform: str = "未归类爬虫"

    # 参数模型类（子类可以定义）
    params_model: type[BaseModel] | None = None

    def __init__(
        self,
        browser_pool: BrowserPool | None = None,
        config: Any | None = None,
    ):
        """
        初始化爬虫

        Args:
            browser_pool: 浏览器池实例
            config: 爬虫配置
        """
        super().__init__(browser_pool, config)

    @abstractmethod
    async def crawl(self, params: Any) -> dict[str, Any] | list[dict[str, Any]]:
        """
        爬虫核心逻辑

        子类必须实现此方法，包含具体的爬取逻辑

        Args:
            params: 验证后的参数对象（Pydantic 模型或字典）

        Returns:
            爬取结果数据
        """
        raise NotImplementedError

    async def postprocess(
        self,
        result: dict[str, Any] | list[dict[str, Any]],
        params: Any,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        结果后处理

        Args:
            result: 原始结果
            params: 使用的参数

        Returns:
            处理后的结果
        """
        return result

    async def run(self, params: dict[str, Any]) -> SpiderResult:
        """
        运行爬虫

        Args:
            params: 爬虫参数（字典格式）

        Returns:
            SpiderResult: 执行结果
        """
        spider_name = self.name or self.__class__.__name__
        started_at = datetime.now()

        logger.info(f"Starting spider: {spider_name}")

        try:
            # 1. 参数验证
            if self.params_model is not None:
                validated_params = self.params_model.model_validate(params)
            else:
                validated_params = params

            # 2. 执行爬取
            result = await self.crawl(validated_params)

            # 3. 结果后处理
            final_result = await self.postprocess(result, validated_params)

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            spider_result = SpiderResult(
                spider_name=spider_name,
                success=True,
                data=final_result,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

            logger.info(f"Spider {spider_name} completed successfully in {duration:.2f}s")

            return spider_result

        except SpiderValidationError as e:
            logger.error(f"Spider {spider_name} validation failed: {e}")
            return self._create_error_result(spider_name, str(e), started_at)

        except SpiderError as e:
            logger.error(f"Spider {spider_name} error: {e}")
            return self._create_error_result(spider_name, str(e), started_at)

        except Exception as e:
            logger.exception(f"Unexpected error in spider {spider_name}: {e}")
            return self._create_error_result(spider_name, str(e), started_at)

    def _create_error_result(
        self,
        spider_name: str,
        error: str,
        started_at: datetime,
    ) -> SpiderResult:
        """创建错误结果"""
        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        return SpiderResult(
            spider_name=spider_name,
            success=False,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
        )

    async def run_batch(
        self,
        params_list: list[dict[str, Any]],
        max_concurrency: int = 3,
    ) -> list[SpiderResult]:
        """
        批量运行爬虫

        Args:
            params_list: 参数列表
            max_concurrency: 最大并发数

        Returns:
            结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def run_with_semaphore(params: dict[str, Any]) -> SpiderResult:
            async with semaphore:
                return await self.run(params)

        tasks = [run_with_semaphore(params) for params in params_list]
        return await asyncio.gather(*tasks)

    @classmethod
    def get_info(cls) -> dict[str, Any]:
        """
        获取爬虫信息

        Returns:
            爬虫元数据字典
        """


        return {
            "name": cls.name or cls.__name__,
            "description": cls.description,
            "version": cls.version,
            "author": cls.author,
            "platform": cls.platform
        }

