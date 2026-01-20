"""
MCP 服务管理器
负责动态创建、挂载和管理 MCP 服务

基于 FastAPI 和 FastMCP 最佳实践实现，修复内存泄漏问题
参考:
- FastAPI GitHub Discussion #9995: 正确的 Mount 删除方法
- FastMCP 官方文档: Lifespan 管理和资源清理
"""

import asyncio
import gc
import inspect
import logging
import weakref
from collections.abc import Callable
from inspect import Parameter
from typing import Any, Literal

from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.tools import Tool
from starlette.routing import Mount

from omnidata.core.spider_register import SpiderRegister
from omnidata.core.exceptions import InitializationError
from omnidata.utils.mcp_utils import generate_tool_description

logger = logging.getLogger(__name__)


class LifespanTaskManager:
    """
    管理 lifespan 上下文的专用 asyncio 任务

    关键改进:
    - 使用弱引用打破循环引用链 (LifespanTaskManager -> FastAPI -> Routes -> Mount)
    - 添加 cleanup() 方法显式清理所有引用
    - 确保 __aenter__ 和 __aexit__ 在同一个任务上下文中调用，避免 ContextVar 错误
    """

    def __init__(self, lifespan_context: Any, app: FastAPI, service_name: str):
        self._lifespan_context = lifespan_context
        # 使用弱引用打破循环引用链，防止内存泄漏
        self._app_ref = weakref.ref(app)
        self._service_name = service_name
        self._task: asyncio.Task | None = None
        self._is_started = False
        self._stop_event = asyncio.Event()
        self._startup_complete = asyncio.Event()
        self._startup_error: Exception | None = None

    async def start(self) -> None:
        """启动 lifespan 管理任务"""
        if self._task is not None:
            return

        self._task = asyncio.create_task(self._lifespan_worker())
        await self._startup_complete.wait()
        if self._startup_error:
            raise self._startup_error
        self._is_started = True

    async def _lifespan_worker(self) -> None:
        """管理 lifespan 上下文的工作任务"""
        try:
            # lifespan 上下文已经绑定了 app，不需要再传递
            await self._lifespan_context.__aenter__()
            self._startup_complete.set()
        except Exception as e:
            self._startup_error = e
            self._startup_complete.set()
            return

        # 等待停止信号
        await self._stop_event.wait()

        # 清理 lifespan
        try:
            await self._lifespan_context.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Lifespan cleanup error for '{self._service_name}': {e}")

    async def stop(self, timeout: float = 5.0) -> None:
        """
        信号通知 lifespan 任务停止

        Args:
            timeout: 等待任务完成的超时时间（秒），默认 5 秒
        """
        if not self._is_started:
            return

        # 发送停止信号
        self._stop_event.set()

        if self._task:
            # 使用超时等待任务完成，防止无限阻塞
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except TimeoutError:
                # 超时后强制取消任务
                logger.warning(
                    f"Lifespan task for '{self._service_name}' did not complete "
                    f"within {timeout}s, cancelling"
                )
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    # 任务已被取消，这是预期行为
                    pass
            except asyncio.CancelledError:
                # 调用方被取消，允许传播
                # 任务会通过 _stop_event 自然完成清理
                logger.debug(f"Stop for '{self._service_name}' was cancelled")
                raise
            finally:
                self._task = None

        self._is_started = False

    def cleanup(self) -> None:
        """
        显式清理所有引用，帮助垃圾回收

        在服务卸载时必须调用，以打破所有可能的引用链
        """
        self._lifespan_context = None
        self._app_ref = None
        self._task = None
        self._stop_event = None
        self._startup_complete = None
        self._startup_error = None


class MCPServiceInfo:
    """
    MCP 服务信息包装类

    关键改进:
    - 添加 cleanup_resources() 方法显式清理所有 FastMCP 相关引用
    - 确保在卸载时彻底释放内存
    """

    def __init__(
        self,
        name: str,
        mcp_server: FastMCP,
        http_app: Any,
        transport: str,
        lifespan_task_manager: LifespanTaskManager | None = None,
    ):
        self.name = name
        self.mcp_server = mcp_server
        self.http_app = http_app
        self.transport = transport
        self.lifespan_task_manager = lifespan_task_manager

    def cleanup_resources(self) -> None:
        """
        清理所有资源引用

        根据 FastMCP 最佳实践，显式断开所有引用以确保资源释放

        清理顺序:
        1. LifespanTaskManager (停止任务并清理引用)
        2. FastMCP 内部工具注册表
        3. FastMCP 实例
        4. HTTP app (Starlette/FastAPI 子应用)
        """
        # 清理 lifespan 管理器
        if self.lifespan_task_manager:
            try:
                self.lifespan_task_manager.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up lifespan manager for '{self.name}': {e}")
            finally:
                self.lifespan_task_manager = None

        # 清理 FastMCP 工具注册表 (FastMCP 内部使用 dict 存储)
        if self.mcp_server is not None:
            try:
                if hasattr(self.mcp_server, '_tools'):
                    self.mcp_server._tools.clear()
                if hasattr(self.mcp_server, '_resources'):
                    self.mcp_server._resources.clear()
                if hasattr(self.mcp_server, '_prompts'):
                    self.mcp_server._prompts.clear()
            except Exception as e:
                logger.warning(f"Error clearing FastMCP registries for '{self.name}': {e}")
            finally:
                self.mcp_server = None

        # 清理 HTTP app 引用
        self.http_app = None

        logger.debug(f"All resources cleaned up for MCP service '{self.name}'")


class MCPManager:
    """
    MCP 服务管理器 - 修复内存泄漏版本

    关键改进:
    1. 使用 FastAPI 官方推荐的 Mount 删除方法 (isinstance + del)
    2. 显式清理 FastMCP 所有资源引用
    3. 使用弱引用打破循环引用链
    4. 清除 FastAPI 路由缓存和 OpenAPI 缓存
    5. 显式调用垃圾回收

    参考:
    - FastAPI GitHub #9995: 正确的 sub-app unmount 方法
    - Starlette 路由实现: Mount 类型检测和删除
    - FastMCP 文档: Lifespan 管理最佳实践
    """

    def __init__(
        self,
        spider_register: SpiderRegister,
        app: FastAPI,
    ) -> None:
        """
        初始化 MCP 管理器

        Args:
            spider_register: Spider 注册表
            app: FastAPI 应用实例
        """
        self._spider_register = spider_register
        self._app = app
        self._services: dict[str, MCPServiceInfo] = {}
        # 并发保护锁
        self._mount_lock = asyncio.Lock()
        # 存储 app 引用，用于 lifespan
        self._fastapi_app = app

    async def mount_service(
        self,
        service_name: str,
        display_name: str,
        description: str,
        transport: Literal["http", "streamable-http", "sse"],
        spider_names: list[str],
        tool_configs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """
        创建并挂载 MCP 服务

        Args:
            service_name: 服务名称（用于路由）
            display_name: 显示名称
            description: 服务描述
            transport: 传输协议 (http, streamable-http, sse)
            spider_names: 要包含的 Spider 名称列表
            tool_configs: 工具配置覆盖 {spider_name: {tool_name, description}}
        """
        # 使用锁确保并发安全
        async with self._mount_lock:
            # 检查是否已存在，先卸载
            if service_name in self._services:
                await self._unmount_service_internal(service_name)

            # 创建 FastMCP 服务器
            mcp_server = FastMCP(
                name=display_name,
                instructions=description,
            )

            # 添加工具（使用去重逻辑防止同名工具重复添加）
            added_tools = set()  # 跟踪已添加的工具名称
            for spider_name in spider_names:
                spider = self._spider_register.get_spider_instance(spider_name)
                if spider is None:
                    continue

                # 获取工具配置（如果有）
                config = tool_configs.get(spider_name, {}) if tool_configs else {}
                tool_name = config.get("tool_name", spider.name)

                # 去重检查：防止同名工具被添加多次
                if tool_name in added_tools:
                    logger.warning(
                        f"Duplicate tool '{tool_name}' (spider: {spider_name}) "
                        f"skipped in service '{service_name}'"
                    )
                    continue
                added_tools.add(tool_name)

                tool_desc = config.get("description", generate_tool_description(spider))

                # 创建带有正确签名的 Spider 包装器
                wrapper = self._create_wrapper_with_signature(spider, tool_name, tool_desc)

                # 使用 Tool.from_function 创建工具并添加到 MCP 服务器
                tool = Tool.from_function(
                    fn=wrapper,
                    name=tool_name,
                    description=tool_desc,
                )
                mcp_server.add_tool(tool)

            # 获取 HTTP 应用，传递 path="/" 避免路径重复
            http_app = mcp_server.http_app(path="/", transport=transport)

            # 处理 lifespan（对于 http 和 streamable-http）
            lifespan_task_manager = None
            if transport in ("http", "streamable-http"):
                try:
                    # 使用 LifespanTaskManager 在专用任务中管理 lifespan
                    # 这确保 __aenter__ 和 __aexit__ 在同一个任务上下文中调用
                    lifespan_context = http_app.lifespan(self._fastapi_app)
                    lifespan_task_manager = LifespanTaskManager(
                        lifespan_context=lifespan_context,
                        app=self._fastapi_app,
                        service_name=service_name,
                    )
                    # 启动 lifespan 任务（确保同上下文的 __aenter__ 和 __aexit__）
                    await lifespan_task_manager.start()
                    logger.debug(f"Started lifespan task for service '{service_name}'")
                except Exception as e:
                    logger.error(f"Failed to initialize lifespan for {service_name}: {e}")
                    await self._unmount_service_internal(service_name)
                    raise

            # 挂载到 FastAPI
            mount_path = f"/mcp/{service_name}"
            self._app.mount(mount_path, http_app)

            # 存储服务信息
            self._services[service_name] = MCPServiceInfo(
                name=service_name,
                mcp_server=mcp_server,
                http_app=http_app,
                transport=transport,
                lifespan_task_manager=lifespan_task_manager,
            )
            logger.info(
                f"MCP service '{service_name}' mounted at {mount_path} (transport={transport})"
            )

    async def _unmount_service_internal(self, service_name: str) -> None:
        """
        内部方法：卸载 MCP 服务（假设已持有锁）

        修复内存泄漏的完整实现，参考 FastAPI GitHub #9995 官方推荐方法

        清理步骤:
        1. 从服务字典中移除（先移除防止重复清理）
        2. 停止 lifespan 任务管理器
        3. 使用 isinstance(Mount) 精确匹配并删除路由
        4. 清除 FastAPI 路由缓存和 OpenAPI 缓存
        5. 显式清理所有 FastMCP 资源引用

        Args:
            service_name: 服务名称
        """
        # 检查服务是否存在
        if service_name not in self._services:
            logger.debug(f"MCP service '{service_name}' not mounted, skipping unmount")
            return

        # 步骤 1: 先从字典中移除（防止重复清理）
        service_info = self._services.pop(service_name)
        mount_path = f"/mcp/{service_name}"

        # 步骤 2: 停止 lifespan 任务管理器（对于 http 和 streamable-http）
        if service_info.lifespan_task_manager is not None:
            try:
                await service_info.lifespan_task_manager.stop()
                logger.debug(f"Lifespan task stopped for '{service_name}'")
            except Exception as e:
                logger.warning(f"Lifespan task stop error for '{service_name}': {e}")

        # 步骤 3: 从 FastAPI 路由表中删除 Mount 对象
        # 使用 FastAPI 官方推荐的方法 (GitHub #9995)
        mount_removed = False
        routes_to_remove = []

        # 首先收集要删除的路由索引
        for index, route in enumerate(list(self._app.router.routes)):
            # 使用 isinstance(Mount) 精确匹配，而非字符串前缀匹配
            if isinstance(route, Mount) and route.path == mount_path:
                routes_to_remove.append(index)
                mount_removed = True
                logger.debug(f"Found Mount route at index {index} for '{mount_path}'")

        # 从后往前删除，避免索引变化
        for index in reversed(routes_to_remove):
            del self._app.router.routes[index]
            logger.debug(f"Removed route at index {index} for '{mount_path}'")

        if not mount_removed:
            logger.warning(
                f"No Mount route found for '{mount_path}', may have been already removed"
            )

        # 步骤 4: 清除路由缓存（重要！防止旧路由被继续使用）
        if hasattr(self._app.router, '_route_cache'):
            self._app.router._route_cache.clear()
            logger.debug(f"Cleared route cache for '{service_name}'")

        # 步骤 5: 清除 OpenAPI 缓存（确保 Swagger 文档更新）
        if hasattr(self._app, 'openapi_schema'):
            self._app.openapi_schema = None
            logger.debug(f"Cleared OpenAPI schema cache for '{service_name}'")

        # 步骤 6: 显式清理服务资源引用（调用 MCPServiceInfo 的清理方法）
        try:
            service_info.cleanup_resources()
        except Exception as e:
            logger.warning(f"Error cleaning up resources for '{service_name}': {e}")

        logger.info(f"MCP service '{service_name}' unmounted and all resources cleaned up")

    async def unmount_service(self, service_name: str) -> None:
        """
        卸载 MCP 服务

        Args:
            service_name: 服务名称
        """
        async with self._mount_lock:
            await self._unmount_service_internal(service_name)

    async def cleanup_all_services(self, timeout: float = 5.0) -> None:
        """
        清理所有挂载的服务

        在应用关闭时调用，会等待所有清理任务完成。

        改进: 添加显式垃圾回收，确保释放所有资源

        Args:
            timeout: 每个服务清理的超时时间（秒）
        """
        service_names = list(self._services.keys())

        async with self._mount_lock:
            for service_name in service_names:
                try:
                    await asyncio.wait_for(
                        self._unmount_service_internal(service_name),
                        timeout=timeout
                    )
                except asyncio.CancelledError:
                    logger.debug(f"Cleanup for service '{service_name}' cancelled during shutdown")
                except TimeoutError:
                    logger.warning(f"Timeout cleaning up service '{service_name}' after {timeout}s")
                except Exception as e:
                    logger.error(f"Error cleaning up service '{service_name}': {e}")

            # 额外保护：确保服务字典被清空
            self._services.clear()

        # 强制垃圾回收（确保释放所有循环引用的资源）
        # 这是修复内存泄漏的关键步骤
        gc.collect()
        logger.info("Forced garbage collection after MCP services cleanup")

    def is_service_mounted(self, service_name: str) -> bool:
        """检查服务是否已挂载"""
        return service_name in self._services

    def _create_wrapper_with_signature(
        self,
        spider: Any,
        tool_name: str,
        tool_desc: str,
    ) -> Callable:
        """
        创建带有动态参数签名的包装器函数

        Args:
            spider: Spider 实例
            tool_name: 工具名称
            tool_desc: 工具描述

        Returns:
            带有正确参数签名的可调用函数
        """
        params_model = getattr(spider, "params_model", None)

        async def wrapper(**kwargs: Any) -> dict[str, Any]:
            """执行 Spider 并返回结果"""
            try:
                # 验证参数
                if params_model:
                    params = params_model(**kwargs)
                else:
                    params = kwargs

                # 执行爬取
                result = await spider.crawl(params)

                # 转换结果为 JSON 可序列化格式
                if isinstance(result, list):
                    return {"results": result}
                return result
            except asyncio.CancelledError:
                # 请求被取消（例如服务停用时的 lifespan 清理）
                logger.debug(f"Spider '{spider.name}' execution cancelled")
                raise
            except Exception as e:
                # 捕获所有其他异常，包括 Playwright 相关的错误
                logger.error(f"Error executing spider '{spider.name}': {e}")
                raise

        # 构建参数签名
        parameters: list[Parameter] = []
        annotations: dict[str, Any] = {}

        if params_model:
            for field_name, field_info in params_model.model_fields.items():
                # 获取默认值
                if field_info.is_required():
                    default_value = Parameter.empty
                else:
                    default_value = field_info.default

                param = Parameter(
                    name=field_name,
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    default=default_value,
                    annotation=field_info.annotation,
                )
                parameters.append(param)
                annotations[field_name] = field_info.annotation

        # 设置函数签名和注解
        wrapper.__signature__ = inspect.Signature(parameters)  # type: ignore
        wrapper.__annotations__ = annotations
        wrapper.__name__ = tool_name
        wrapper.__doc__ = tool_desc

        return wrapper


# 全局 MCP 管理器实例
_mcp_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager:
    """
    获取全局 MCP 管理器实例（同步，无锁）

    Returns:
        MCPManager: MCP 管理器实例

    Raises:
        InitializationError: 未初始化
    """
    global _mcp_manager
    if _mcp_manager is None:
        raise InitializationError(
            "MCPManager not initialized. "
            "Ensure main.py lifespan startup completes before calling this function."
        )
    return _mcp_manager


def set_mcp_manager(instance: MCPManager) -> None:
    """
    设置全局 MCP 管理器实例（由 main.py lifespan 调用）

    Args:
        instance: MCP 管理器实例
    """
    global _mcp_manager
    _mcp_manager = instance
