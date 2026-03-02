"""
爬虫基类模块
提供爬虫的通用功能，子类只需实现 crawl 方法
"""

import asyncio
import json
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .base_helper import BaseHelper
from .browser_context_pool import BrowserContextPool
from .exceptions import SpiderError, SpiderValidationError

logger = logging.getLogger(__name__)


@dataclass
class SpiderResult:
    """爬虫执行结果"""

    success: bool = True
    data: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    message: str | None = None
    # 以下字段设置了也没有用，会自动在run方法中覆盖，开发者无需关注，专注于上方的字段设置即可
    spider_name: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "spider_name": self.spider_name,
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


class BaseWebSpider(BaseHelper):
    """
    爬虫基类

    子类需要实现以下方法:
        - crawl: 具体的爬取逻辑（必需），返回 SpiderResult
        - postprocess: 结果后处理（可选），接收并返回 SpiderResult

    使用示例:
        ```python
        from pydantic import BaseModel, Field
        from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult

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

            async def crawl(self, params: MyParams) -> SpiderResult:
                # 通过 browser_context_pool.get_context() 获取上下文
                async with self.browser_context_pool.get_context() as context:
                    page = await context.new_page()
                    try:
                        await page.goto(params.url)
                        title = await page.title()

                        # 直接返回 SpiderResult，spider_name 和时间字段由 run 方法自动设置
                        return SpiderResult(
                            success=True,
                            data={"title": title, "url": params.url},
                        )
                    finally:
                        await page.close()
        ```

    属性说明:
        - self.config: 爬虫配置对象
        - self.browser_context_pool: 浏览器上下文池实例

    可用方法:
        - async with self.browser_context_pool.get_context(namespace="xxx", use_stealth=True): 获取浏览器上下文
        - 用户需自行从 context 创建 page: page = await context.new_page()
    """

    # 爬虫名称，整个系统中需要唯一标识，统一以 数据源+下划线+爬虫名称编码，如 eastmoney_news_query
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    # 平台名称，就统一设置为对应数据源的中文名称
    platform: str = "未归类爬虫"

    # 参数模型类（子类可以定义）
    params_model: type[BaseModel] | None = None

    def __init__(
        self,
        browser_context_pool: BrowserContextPool | None = None,
        config: Any | None = None,
    ):
        """
        初始化爬虫

        Args:
            browser_context_pool: 浏览器上下文池实例
            config: 爬虫配置
        """
        super().__init__(browser_context_pool, config)

    @abstractmethod
    async def crawl(self, params: Any) -> SpiderResult:
        """
        爬虫核心逻辑

        子类必须实现此方法，包含具体的爬取逻辑

        Args:
            params: 验证后的参数对象（Pydantic 模型或字典）

        Returns:
            SpiderResult: 执行结果
        """
        raise NotImplementedError

    async def postprocess(
        self,
        result: SpiderResult,
        params: Any,
    ) -> SpiderResult:
        """
        结果后处理

        Args:
            result: 爬虫执行结果
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
            validated_params: Any
            if self.params_model is not None:
                validated_params = self.params_model.model_validate(params)
            else:
                validated_params = params

            # 2. 执行爬取（crawl 返回 SpiderResult）
            result = await self.crawl(validated_params)

            # 3. 结果后处理（postprocess 处理 SpiderResult）
            final_result = await self.postprocess(result, validated_params)

            # 4. 设置 spider_name 和时间字段（包含 crawl + postprocess 的总时间）
            completed_at = datetime.now()
            final_result.spider_name = spider_name
            final_result.started_at = started_at
            final_result.completed_at = completed_at
            final_result.duration_seconds = (completed_at - started_at).total_seconds()

            logger.info(
                f"Spider {spider_name} completed successfully in {final_result.duration_seconds:.2f}s"
            )

            # 5. 记录审计日志
            await self._audit_spider_run(final_result, validated_params)

            return final_result

        except SpiderValidationError as e:
            logger.error(f"Spider {spider_name} validation failed: {e}")
            error_result = self._create_error_result(spider_name, str(e), started_at)
            await self._audit_spider_run(error_result, params)
            return error_result

        except SpiderError as e:
            logger.error(f"Spider {spider_name} error: {e}")
            error_result = self._create_error_result(spider_name, str(e), started_at)
            await self._audit_spider_run(error_result, params)
            return error_result

        except Exception as e:
            logger.exception(f"Unexpected error in spider {spider_name}: {e}")
            error_result = self._create_error_result(spider_name, str(e), started_at)
            await self._audit_spider_run(error_result, params)
            return error_result

    def _create_error_result(
        self,
        spider_name: str,
        error: str,
        started_at: datetime,
    ) -> SpiderResult:
        """创建错误结果"""
        completed_at = datetime.now()
        return SpiderResult(
            spider_name=spider_name,
            success=False,
            message=error,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
        )

    async def _audit_spider_run(self, result: SpiderResult, params: Any) -> None:
        """
        记录爬虫执行审计日志

        Args:
            result: 爬虫执行结果
            params: 爬虫参数
        """
        try:
            from omnidata.database import get_db_session
            from omnidata.database.models import SpiderAudit

            # 将 params 转换为可序列化的格式
            if params is None:
                params_json = None
            elif isinstance(params, dict):
                params_json = json.dumps(params, ensure_ascii=False)
            elif hasattr(params, "model_dump"):  # Pydantic 模型
                params_json = json.dumps(params.model_dump(mode="json"), ensure_ascii=False)
            else:
                params_json = json.dumps(str(params), ensure_ascii=False)

            # 将 metadata 转换为 JSON
            metadata_json = (
                json.dumps(result.metadata, ensure_ascii=False) if result.metadata else None
            )

            async with get_db_session() as session:
                audit_record = SpiderAudit(
                    spider_name=result.spider_name,
                    platform=self.platform,
                    spider_version=self.version,
                    success=result.success,
                    error_message=result.message if not result.success else None,
                    started_at=result.started_at,
                    completed_at=result.completed_at,
                    duration_seconds=result.duration_seconds,
                    params=params_json,
                    result_metadata=metadata_json,
                )
                session.add(audit_record)
        except Exception as e:
            # 审计记录失败不应影响爬虫执行
            logger.warning(f"Failed to audit spider run: {e}")

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
            "platform": cls.platform,
        }
