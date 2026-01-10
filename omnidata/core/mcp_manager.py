"""
MCP 服务管理器
负责动态创建、挂载和管理 MCP 服务
"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from inspect import Parameter
from typing import Any, Literal

from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.tools import Tool

from omnidata.core.spider_register import SpiderRegister
from omnidata.utils.mcp_utils import generate_tool_description

logger = logging.getLogger(__name__)


class MCPServiceInfo:
    """MCP 服务信息"""

    def __init__(
        self,
        name: str,
        mcp_server: FastMCP,
        http_app: Any,
        transport: str,
        lifespan_context: Any | None = None,
        creation_task: asyncio.Task | None = None,
        cleanup_task: asyncio.Task | None = None,
    ):
        self.name = name
        self.mcp_server = mcp_server
        self.http_app = http_app
        self.transport = transport
        self.lifespan_context = lifespan_context
        self.creation_task = creation_task
        self.cleanup_task = cleanup_task


class MCPManager:
    """
    MCP 服务管理器

    负责动态创建和挂载 MCP 服务到 FastAPI 应用
    正确处理所有传输模式（http, streamable-http, sse）的 lifespan 管理
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
        # 存储待清理的服务（lifespan exit 必须在相同上下文中执行）
        # HTTP 请求上下文无法执行 lifespan exit，需要延迟到 shutdown 时执行
        self._pending_cleanup: list[MCPServiceInfo] = []

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
                        f"Duplicate tool '{tool_name}' (spider: {spider_name}) skipped in service '{service_name}'"
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
            lifespan_context = None
            creation_task = None
            if transport in ("http", "streamable-http"):
                try:
                    # 根据 FastMCP 文档，需要手动管理 lifespan
                    # https://gofastmcp.com/integrations/fastapi
                    creation_task = asyncio.current_task()
                    lifespan_context = http_app.lifespan(self._fastapi_app)
                    # 进入 lifespan 上下文以初始化 session manager
                    await lifespan_context.__aenter__()
                    logger.debug(f"Initialized lifespan for service '{service_name}'")
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
                lifespan_context=lifespan_context,
                creation_task=creation_task,
                cleanup_task=None,
            )
            logger.info(f"MCP service '{service_name}' mounted at {mount_path} (transport={transport})")

    async def _unmount_service_internal(self, service_name: str, in_shutdown_context: bool = False) -> None:
        """
        内部方法：卸载 MCP 服务（假设已持有锁）

        清理 lifespan 上下文并从 FastAPI 中移除路由

        Args:
            service_name: 服务名称
            in_shutdown_context: 是否在 shutdown 上下文中调用（True 可以执行 lifespan exit）
        """
        if service_name in self._services:
            service_info = self._services[service_name]

            # 处理 lifespan 上下文清理（对于 http 和 streamable-http）
            if service_info.lifespan_context is not None:
                if in_shutdown_context:
                    # 在 shutdown 上下文中，可以直接执行 lifespan exit
                    try:
                        await service_info.lifespan_context.__aexit__(None, None, None)
                        logger.debug(f"Lifespan cleanup completed for '{service_name}'")
                    except Exception as e:
                        logger.warning(f"Lifespan cleanup error for '{service_name}': {e}")
                else:
                    # 在 HTTP 请求上下文中，将服务添加到待清理列表
                    # lifespan exit 必须在相同上下文（shutdown）中执行
                    self._pending_cleanup.append(service_info)
                    logger.debug(f"Service '{service_name}' marked for pending lifespan cleanup")

            # 从 FastAPI 中移除路由（所有 transport 都需要）
            mount_path = f"/mcp/{service_name}"
            self._app.router.routes = [
                r for r in self._app.router.routes
                if not getattr(r, "path", "").startswith(mount_path)
            ]

            # 删除缓存（使用 pop 避免 KeyError，使方法幂等）
            self._services.pop(service_name, None)
            logger.info(f"MCP service '{service_name}' unmounted")
        else:
            logger.debug(f"MCP service '{service_name}' not mounted, skipping unmount")

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
        首先清理待清理列表中的服务（之前通过 HTTP 请求卸载的），
        然后卸载当前挂载的服务。

        Args:
            timeout: 每个服务清理的超时时间（秒）
        """
        # 阶段 1: 清理待清理列表中的服务（lifespan exit 必须在 shutdown 上下文中执行）
        for service_info in self._pending_cleanup:
            if service_info.lifespan_context is not None:
                try:
                    await asyncio.wait_for(
                        service_info.lifespan_context.__aexit__(None, None, None),
                        timeout=timeout
                    )
                    logger.debug(f"Pending lifespan cleanup completed for '{service_info.name}'")
                except asyncio.CancelledError:
                    logger.debug(f"Pending cleanup for '{service_info.name}' cancelled during shutdown")
                except asyncio.TimeoutError:
                    logger.warning(f"Pending cleanup timeout for '{service_info.name}' after {timeout}s")
                except Exception as e:
                    logger.warning(f"Pending cleanup error for '{service_info.name}': {e}")
        self._pending_cleanup.clear()

        # 阶段 2: 卸载当前挂载的服务
        service_names = list(self._services.keys())

        async with self._mount_lock:
            for service_name in service_names:
                try:
                    # 直接调用内部方法，传递 in_shutdown_context=True 以执行 lifespan exit
                    await asyncio.wait_for(
                        self._unmount_service_internal(service_name, in_shutdown_context=True),
                        timeout=timeout
                    )
                except asyncio.CancelledError:
                    logger.debug(f"Cleanup for service '{service_name}' cancelled during shutdown")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout cleaning up service '{service_name}' after {timeout}s")
                except Exception as e:
                    logger.error(f"Error cleaning up service '{service_name}': {e}")

            # 额外保护：确保服务字典被清空
            self._services.clear()

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
_mcp_manager_lock = asyncio.Lock()


async def get_mcp_manager() -> MCPManager:
    """获取全局 MCP 管理器实例"""
    global _mcp_manager
    if _mcp_manager is None:
        async with _mcp_manager_lock:
            # 双重检查锁定
            if _mcp_manager is None:
                from omnidata.api.main import app
                from omnidata.core.spider_register import get_spider_register

                spider_reg = await get_spider_register()
                _mcp_manager = MCPManager(spider_reg, app)
    return _mcp_manager
