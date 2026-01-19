"""
MCP 服务管理路由
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from omnidata.api.responses import error_response, success_response
from omnidata.core.mcp_manager import get_mcp_manager
from omnidata.core.spider_register import get_spider_register
from omnidata.database import get_db_session
from omnidata.database.models import MCPService, MCPTool, SpiderPrompt
from omnidata.utils.mcp_utils import (
    extract_parameter_info,
    generate_tool_description,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mcp-services", tags=["mcp-services"])


# ========== Request Models ==========


class MCPToolCreate(BaseModel):
    """创建 MCP 工具请求"""

    spider_name: str = Field(..., description="Spider 名称")
    tool_name: str | None = Field(None, description="自定义工具名称（默认使用 Spider 名称）")


class MCPServiceCreate(BaseModel):
    """创建 MCP 服务请求"""

    name: str = Field(..., description="服务名称（用于路由，唯一）", min_length=1, max_length=100)
    display_name: str = Field(..., description="显示名称", min_length=1, max_length=200)
    description: str = Field("", description="服务描述")
    transport: str = Field(
        "http",
        description="传输协议",
        pattern="^(http|streamable-http|sse)$",
    )
    tools: list[MCPToolCreate] = Field(..., description="工具列表", min_length=1)


class MCPServiceUpdate(BaseModel):
    """更新 MCP 服务请求"""

    display_name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None)
    transport: str | None = Field(None, pattern="^(http|streamable-http|sse)$")
    tools: list[MCPToolCreate] | None = Field(None, description="工具列表（完整替换）")


class ToolPromptVersionUpdate(BaseModel):
    """设置工具提示词版本请求"""

    version_name: str = Field(..., description="要使用的提示词版本名称")


# ========== Service CRUD Endpoints ==========


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_service(request: MCPServiceCreate):
    """
    创建新的 MCP 服务

    创建一个新的 MCP 服务，将指定的 Spider 作为工具暴露。
    服务将自动挂载到 `/mcp/{name}` 路径。
    """
    async with get_db_session() as session:
        # 检查名称是否已存在
        existing = await session.execute(
            select(MCPService).where(MCPService.name == request.name)
        )
        if existing.scalar_one_or_none():
            return error_response(f"服务名称 '{request.name}' 已存在")

        # 验证所有 Spider 都存在
        spider_reg = get_spider_register()
        spider_names = [t.spider_name for t in request.tools]
        for spider_name in spider_names:
            spider = spider_reg.get_spider_instance(spider_name)
            if spider is None:
                return error_response(f"Spider '{spider_name}' 不存在")

        # 创建服务
        service = MCPService(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            transport=request.transport,
            is_active=True,
        )
        session.add(service)
        await session.flush()

        # 创建工具并确保每个 Spider 有默认提示词
        tool_configs: dict[str, dict[str, Any]] = {}
        for tool_req in request.tools:
            spider = spider_reg.get_spider_instance(tool_req.spider_name)
            tool_name = tool_req.tool_name or spider.name
            default_desc = generate_tool_description(spider)

            # 确保有默认提示词
            await _ensure_default_spider_prompt(session, tool_req.spider_name, spider)

            # 创建工具（selected_prompt_version 为空，表示使用默认版本）
            tool = MCPTool(
                service_id=service.id,
                spider_name=tool_req.spider_name,
                tool_name=tool_name,
                enabled=True,
                selected_prompt_version=None,
            )
            session.add(tool)
            await session.flush()

            tool_configs[tool_req.spider_name] = {
                "tool_name": tool_name,
                "description": default_desc,
            }

        await session.commit()
        await session.refresh(service)

        # 挂载服务
        mcp_manager = get_mcp_manager()
        await mcp_manager.mount_service(
            service_name=service.name,
            display_name=service.display_name,
            description=service.description,
            transport=service.transport,
            spider_names=spider_names,
            tool_configs=tool_configs,
        )

        return success_response({
            "id": service.id,
            "name": service.name,
            "display_name": service.display_name,
            "description": service.description or "",
            "transport": service.transport,
            "is_active": service.is_active,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "tool_count": len(request.tools),
        }, "MCP 服务创建成功")


@router.get("")
async def list_services(is_active: bool | None = None):
    """
    列出所有 MCP 服务

    可以通过 `is_active` 参数过滤服务状态。
    """
    async with get_db_session() as session:
        query = select(MCPService).options(selectinload(MCPService.tools))
        if is_active is not None:
            query = query.where(MCPService.is_active == is_active)

        result = await session.execute(query.order_by(MCPService.created_at.desc()))
        services = result.scalars().all()

        return success_response([
            {
                "id": s.id,
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description or "",
                "transport": s.transport,
                "is_active": s.is_active,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "tool_count": len(s.tools),
            }
            for s in services
        ], "获取 MCP 服务列表成功")


@router.get("/{service_id}")
async def get_service(service_id: int):
    """获取指定 MCP 服务的详细信息"""
    async with get_db_session() as session:
        result = await session.execute(
            select(MCPService).options(selectinload(MCPService.tools)).where(MCPService.id == service_id)
        )
        service = result.scalar_one_or_none()

        if not service:
            return error_response("服务不存在")

        return success_response({
            "id": service.id,
            "name": service.name,
            "display_name": service.display_name,
            "description": service.description or "",
            "transport": service.transport,
            "is_active": service.is_active,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "tool_count": len(service.tools),
        }, "获取 MCP 服务详情成功")


@router.put("/{service_id}")
async def update_service(service_id: int, request: MCPServiceUpdate):
    """更新 MCP 服务"""
    async with get_db_session() as session:
        result = await session.execute(
            select(MCPService)
            .options(selectinload(MCPService.tools))
            .where(MCPService.id == service_id)
        )
        service = result.scalar_one_or_none()

        if not service:
            return error_response("服务不存在")

        # 更新字段
        if request.display_name is not None:
            service.display_name = request.display_name
        if request.description is not None:
            service.description = request.description
        if request.transport is not None:
            service.transport = request.transport

        # 处理工具列表更新（如果提供）
        if request.tools is not None:
            # 验证所有 Spider 存在
            spider_reg = get_spider_register()
            requested_spider_names = {t.spider_name for t in request.tools}

            for spider_name in requested_spider_names:
                spider = spider_reg.get_spider_instance(spider_name)
                if spider is None:
                    return error_response(f"Spider '{spider_name}' 不存在")

            # 当前工具列表
            current_spider_names = {t.spider_name for t in service.tools}

            # 计算需要添加和删除的 spiders
            spiders_to_add = requested_spider_names - current_spider_names
            spiders_to_remove = current_spider_names - requested_spider_names

            # 删除不再需要的工具
            if spiders_to_remove:
                await session.execute(
                    delete(MCPTool).where(
                        MCPTool.service_id == service_id,
                        MCPTool.spider_name.in_(spiders_to_remove)
                    )
                )

            # 添加新工具
            for spider_name in spiders_to_add:
                spider = spider_reg.get_spider_instance(spider_name)
                tool_name = spider.name  # 使用 Spider 名称作为工具名称

                # 确保有默认提示词
                await _ensure_default_spider_prompt(session, spider_name, spider)

                # 创建工具（使用默认提示词版本）
                tool = MCPTool(
                    service_id=service_id,
                    spider_name=spider_name,
                    tool_name=tool_name,
                    enabled=True,
                    selected_prompt_version=None,
                )
                session.add(tool)

            # 刷新服务以获取更新后的工具列表
            await session.flush()
            await session.refresh(service, ["tools"])

        await session.commit()
        await session.refresh(service)

        # 重新挂载服务
        mcp_manager = get_mcp_manager()

        try:
            await mcp_manager.unmount_service(service.name)

            spider_names = [t.spider_name for t in service.tools if t.enabled]
            tool_configs = {}
            for t in service.tools:
                if t.enabled:
                    prompt = await _get_active_tool_prompt(session, t)
                    desc = prompt.description if prompt else ""
                    tool_configs[t.spider_name] = {"tool_name": t.tool_name, "description": desc}

            await mcp_manager.mount_service(
                service_name=service.name,
                display_name=service.display_name,
                description=service.description or "",
                transport=service.transport,
                spider_names=spider_names,
                tool_configs=tool_configs,
            )
        except Exception as e:
            # 挂载失败，自动停用服务并返回错误
            logging.error(f"Failed to remount service {service.name}: {e}, deactivating...")
            async with get_db_session() as rollback_session:
                await rollback_session.execute(
                    update(MCPService)
                    .where(MCPService.id == service_id)
                    .values(is_active=False)
                )
                await rollback_session.commit()
            return error_response(f"挂载服务失败: {str(e)}。服务已自动停用。")

        return success_response({
            "id": service.id,
            "name": service.name,
            "display_name": service.display_name,
            "description": service.description or "",
            "transport": service.transport,
            "is_active": service.is_active,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "tool_count": len(service.tools),
        }, "MCP 服务更新成功")


@router.delete("/{service_id}")
async def delete_service(service_id: int):
    """删除 MCP 服务"""
    async with get_db_session() as session:
        result = await session.execute(
            select(MCPService)
            .options(selectinload(MCPService.tools))  # 预加载工具关系
            .where(MCPService.id == service_id)
        )
        service = result.scalar_one_or_none()

        if not service:
            return error_response("服务不存在")

        service_name = service.name

        # 使用 SQLAlchemy ORM 删除（会触发 cascade="all, delete-orphan"）
        await session.delete(service)
        await session.commit()

        # 卸载服务
        mcp_manager = get_mcp_manager()
        await mcp_manager.unmount_service(service_name)

        return success_response(None, "MCP 服务删除成功")


@router.put("/{service_id}/activate")
async def activate_service(service_id: int):
    """激活 MCP 服务"""
    async with get_db_session() as session:
        result = await session.execute(
            select(MCPService)
            .options(selectinload(MCPService.tools))
            .where(MCPService.id == service_id)
        )
        service = result.scalar_one_or_none()

        if not service:
            return error_response("服务不存在")

        service.is_active = True
        await session.commit()
        await session.refresh(service)

        # 挂载 MCP 服务（捕获所有异常，确保服务状态已更新）
        mcp_manager = get_mcp_manager()
        spider_names = [t.spider_name for t in service.tools if t.enabled]
        tool_configs = {}
        for t in service.tools:
            if t.enabled:
                prompt = await _get_active_tool_prompt(session, t)
                desc = prompt.description if prompt else ""
                tool_configs[t.spider_name] = {"tool_name": t.tool_name, "description": desc}

        try:
            await mcp_manager.mount_service(
                service_name=service.name,
                display_name=service.display_name,
                description=service.description or "",
                transport=service.transport,
                spider_names=spider_names,
                tool_configs=tool_configs,
            )
        except Exception as e:
            logger.warning(f"Error mounting service '{service.name}' during activation: {e}")

        return success_response({
            "id": service.id,
            "name": service.name,
            "display_name": service.display_name,
            "description": service.description or "",
            "transport": service.transport,
            "is_active": service.is_active,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "tool_count": len(service.tools),
        }, "MCP 服务激活成功")


@router.put("/{service_id}/deactivate")
async def deactivate_service(service_id: int):
    """停用 MCP 服务"""
    async with get_db_session() as session:
        result = await session.execute(
            select(MCPService).options(selectinload(MCPService.tools)).where(MCPService.id == service_id)
        )
        service = result.scalar_one_or_none()

        if not service:
            return error_response("服务不存在")

        service.is_active = False
        await session.commit()
        await session.refresh(service)

        # 卸载 MCP 服务（捕获所有异常，确保服务状态已更新）
        mcp_manager = get_mcp_manager()
        try:
            await mcp_manager.unmount_service(service.name)
        except asyncio.CancelledError:
            # CancelledError 在停用服务时是预期的，因为 lifespan 清理会中断正在进行的请求
            logger.debug(f"Service '{service.name}' deactivation caused request cancellation (expected)")
        except Exception as e:
            logger.warning(f"Error unmounting service '{service.name}' during deactivation: {e}")

        return success_response({
            "id": service.id,
            "name": service.name,
            "display_name": service.display_name,
            "description": service.description or "",
            "transport": service.transport,
            "is_active": service.is_active,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "tool_count": len(service.tools),
        }, "MCP 服务停用成功")


# ========== Tool Management Endpoints ==========


@router.get("/{service_id}/tools")
async def list_service_tools(service_id: int):
    """列出服务的所有工具"""
    async with get_db_session() as session:
        # 验证服务存在
        service_result = await session.execute(
            select(MCPService).where(MCPService.id == service_id)
        )
        service = service_result.scalar_one_or_none()
        if not service:
            return error_response("服务不存在")

        # 查询工具
        result = await session.execute(
            select(MCPTool)
            .where(MCPTool.service_id == service_id)
        )
        tools = result.scalars().all()

        responses = []
        for t in tools:
            prompt = await _get_active_tool_prompt(session, t)
            responses.append({
                "id": t.id,
                "service_id": t.service_id,
                "spider_name": t.spider_name,
                "tool_name": t.tool_name,
                "enabled": t.enabled,
                "selected_prompt_version": t.selected_prompt_version,
                "current_prompt_version_name": prompt.version_name if prompt else None,
                "current_prompt_description": prompt.description if prompt else None,
            })

        return success_response(responses, "获取服务工具列表成功")


@router.post("/{service_id}/tools", status_code=status.HTTP_201_CREATED)
async def add_tool_to_service(service_id: int, request: MCPToolCreate):
    """向服务添加新工具"""
    async with get_db_session() as session:
        # 验证服务存在
        service_result = await session.execute(
            select(MCPService)
            .options(selectinload(MCPService.tools))
            .where(MCPService.id == service_id)
        )
        service = service_result.scalar_one_or_none()
        if not service:
            return error_response("服务不存在")

        # 验证 Spider 存在
        spider_reg = get_spider_register()
        spider = spider_reg.get_spider_instance(request.spider_name)
        if not spider:
            return error_response(f"Spider '{request.spider_name}' 不存在")

        # 检查是否已存在
        existing = await session.execute(
            select(MCPTool).where(
                MCPTool.service_id == service_id, MCPTool.spider_name == request.spider_name
            )
        )
        if existing.scalar_one_or_none():
            return error_response(f"该服务中已存在 Spider '{request.spider_name}' 的工具")

        # 确保有默认提示词
        await _ensure_default_spider_prompt(session, request.spider_name, spider)

        # 创建工具
        tool_name = request.tool_name or spider.name
        default_desc = generate_tool_description(spider)

        tool = MCPTool(
            service_id=service_id,
            spider_name=request.spider_name,
            tool_name=tool_name,
            enabled=True,
            selected_prompt_version=None,
        )
        session.add(tool)
        await session.commit()
        await session.refresh(tool)

        # 重新挂载服务
        mcp_manager = get_mcp_manager()
        await mcp_manager.unmount_service(service.name)

        spider_names = [t.spider_name for t in service.tools if t.enabled] + [request.spider_name]
        tool_configs = {
            t.spider_name: {
                "tool_name": t.tool_name,
                "description": (await _get_active_tool_prompt(session, t)).description or ""
            }
            for t in service.tools
            if t.enabled
        }
        tool_configs[request.spider_name] = {"tool_name": tool_name, "description": default_desc}

        await mcp_manager.mount_service(
            service_name=service.name,
            display_name=service.display_name,
            description=service.description or "",
            transport=service.transport,
            spider_names=spider_names,
            tool_configs=tool_configs,
        )

        return success_response({
            "id": tool.id,
            "service_id": tool.service_id,
            "spider_name": tool.spider_name,
            "tool_name": tool.tool_name,
            "enabled": tool.enabled,
            "selected_prompt_version": tool.selected_prompt_version,
            "current_prompt_description": default_desc,
        }, "工具添加成功")


@router.delete("/{service_id}/tools/{tool_id}")
async def remove_tool_from_service(service_id: int, tool_id: int):
    """从服务中移除工具"""
    async with get_db_session() as session:
        # 验证服务存在
        service_result = await session.execute(
            select(MCPService)
            .options(selectinload(MCPService.tools))
            .where(MCPService.id == service_id)
        )
        service = service_result.scalar_one_or_none()
        if not service:
            return error_response("服务不存在")

        # 查找工具
        result = await session.execute(
            select(MCPTool).where(MCPTool.id == tool_id, MCPTool.service_id == service_id)
        )
        tool = result.scalar_one_or_none()
        if not tool:
            return error_response("工具不存在")

        spider_name = tool.spider_name

        # 删除工具
        await session.execute(delete(MCPTool).where(MCPTool.id == tool_id))
        await session.commit()

        # 重新挂载服务
        mcp_manager = get_mcp_manager()
        await mcp_manager.unmount_service(service.name)

        spider_names = [t.spider_name for t in service.tools if t.enabled and t.spider_name != spider_name]
        tool_configs = {
            t.spider_name: {
                "tool_name": t.tool_name,
                "description": (await _get_active_tool_prompt(session, t)).description or ""
            }
            for t in service.tools
            if t.enabled and t.spider_name != spider_name
        }

        await mcp_manager.mount_service(
            service_name=service.name,
            display_name=service.display_name,
            description=service.description or "",
            transport=service.transport,
            spider_names=spider_names,
            tool_configs=tool_configs,
        )

        return success_response(None, "工具移除成功")


# ========== Tool Prompt Version Management Endpoints ==========


@router.get("/{service_id}/tools/{tool_id}/prompt-version")
async def get_tool_prompt_version(service_id: int, tool_id: int):
    """获取工具当前使用的提示词版本"""
    async with get_db_session() as session:
        # 验证服务和工具存在
        tool_result = await session.execute(
            select(MCPTool).where(MCPTool.id == tool_id, MCPTool.service_id == service_id)
        )
        tool = tool_result.scalar_one_or_none()
        if not tool:
            return error_response("工具不存在")

        # 获取当前使用的提示词
        current_prompt = await _get_active_tool_prompt(session, tool)

        # 获取该 Spider 的所有可用提示词版本
        prompts_result = await session.execute(
            select(SpiderPrompt)
            .where(SpiderPrompt.spider_name == tool.spider_name)
            .order_by(SpiderPrompt.is_default.desc(), SpiderPrompt.created_at.asc())
        )
        all_prompts = prompts_result.scalars().all()

        available_versions = [
            {"version_name": p.version_name, "description": p.description, "is_default": p.is_default}
            for p in all_prompts
        ]

        return success_response({
            "tool_id": tool.id,
            "spider_name": tool.spider_name,
            "current_version": current_prompt.version_name if current_prompt else None,
            "current_description": current_prompt.description if current_prompt else None,
            "available_versions": available_versions,
        }, "获取工具提示词版本成功")


@router.put("/{service_id}/tools/{tool_id}/prompt-version")
async def set_tool_prompt_version(service_id: int, tool_id: int, request: ToolPromptVersionUpdate):
    """设置工具使用的提示词版本"""
    async with get_db_session() as session:
        # 验证服务和工具存在（预加载 tools 关系）
        service_result = await session.execute(
            select(MCPService)
            .options(selectinload(MCPService.tools))
            .where(MCPService.id == service_id)
        )
        service = service_result.scalar_one_or_none()
        if not service:
            return error_response("服务不存在")

        tool_result = await session.execute(
            select(MCPTool).where(MCPTool.id == tool_id, MCPTool.service_id == service_id)
        )
        tool = tool_result.scalar_one_or_none()
        if not tool:
            return error_response("工具不存在")

        # 验证提示词版本存在
        prompt_result = await session.execute(
            select(SpiderPrompt).where(
                SpiderPrompt.spider_name == tool.spider_name,
                SpiderPrompt.version_name == request.version_name
            )
        )
        prompt = prompt_result.scalar_one_or_none()
        if not prompt:
            return error_response(f"Spider '{tool.spider_name}' 不存在提示词版本 '{request.version_name}'")

        # 更新工具的提示词版本
        tool.selected_prompt_version = request.version_name if not prompt.is_default else None
        await session.commit()

        # 重新挂载服务（捕获所有异常，确保提示词版本已更新）
        mcp_manager = get_mcp_manager()
        try:
            await mcp_manager.unmount_service(service.name)
        except Exception as e:
            logger.warning(f"Error unmounting service '{service.name}' during prompt version change: {e}")

        # 重新加载所有工具配置
        spider_names = [t.spider_name for t in service.tools if t.enabled]
        tool_configs = {}
        for t in service.tools:
            if t.enabled:
                active_prompt = await _get_active_tool_prompt(session, t)
                desc = active_prompt.description if active_prompt else ""
                tool_configs[t.spider_name] = {"tool_name": t.tool_name, "description": desc}

        try:
            await mcp_manager.mount_service(
                service_name=service.name,
                display_name=service.display_name,
                description=service.description or "",
                transport=service.transport,
                spider_names=spider_names,
                tool_configs=tool_configs,
            )
        except Exception as e:
            logger.warning(f"Error mounting service '{service.name}' during prompt version change: {e}")

        # 获取所有可用版本
        prompts_result = await session.execute(
            select(SpiderPrompt)
            .where(SpiderPrompt.spider_name == tool.spider_name)
            .order_by(SpiderPrompt.is_default.desc(), SpiderPrompt.created_at.asc())
        )
        all_prompts = prompts_result.scalars().all()

        available_versions = [
            {"version_name": p.version_name, "description": p.description, "is_default": p.is_default}
            for p in all_prompts
        ]

        return success_response({
            "tool_id": tool.id,
            "spider_name": tool.spider_name,
            "current_version": prompt.version_name if not prompt.is_default else None,
            "current_description": prompt.description,
            "available_versions": available_versions,
        }, "工具提示词版本设置成功")


@router.delete("/{service_id}/tools/{tool_id}/prompt-version")
async def clear_tool_prompt_version(service_id: int, tool_id: int):
    """清除工具的自定义提示词版本，恢复使用默认版本"""
    async with get_db_session() as session:
        # 验证服务和工具存在（预加载 tools 关系）
        service_result = await session.execute(
            select(MCPService)
            .options(selectinload(MCPService.tools))
            .where(MCPService.id == service_id)
        )
        service = service_result.scalar_one_or_none()
        if not service:
            return error_response("服务不存在")

        tool_result = await session.execute(
            select(MCPTool).where(MCPTool.id == tool_id, MCPTool.service_id == service_id)
        )
        tool = tool_result.scalar_one_or_none()
        if not tool:
            return error_response("工具不存在")

        # 清除自定义版本，恢复默认
        tool.selected_prompt_version = None
        await session.commit()

        # 重新挂载服务（捕获所有异常，确保提示词版本已更新）
        mcp_manager = get_mcp_manager()
        try:
            await mcp_manager.unmount_service(service.name)
        except Exception as e:
            logger.warning(f"Error unmounting service '{service.name}' during prompt version clear: {e}")

        spider_names = [t.spider_name for t in service.tools if t.enabled]
        tool_configs = {}
        for t in service.tools:
            if t.enabled:
                active_prompt = await _get_active_tool_prompt(session, t)
                desc = active_prompt.description if active_prompt else ""
                tool_configs[t.spider_name] = {"tool_name": t.tool_name, "description": desc}

        try:
            await mcp_manager.mount_service(
                service_name=service.name,
                display_name=service.display_name,
                description=service.description or "",
                transport=service.transport,
                spider_names=spider_names,
                tool_configs=tool_configs,
            )
        except Exception as e:
            logger.warning(f"Error mounting service '{service.name}' during prompt version clear: {e}")

        # 获取默认提示词
        default_prompt = await _get_active_tool_prompt(session, tool)

        # 获取所有可用版本
        prompts_result = await session.execute(
            select(SpiderPrompt)
            .where(SpiderPrompt.spider_name == tool.spider_name)
            .order_by(SpiderPrompt.is_default.desc(), SpiderPrompt.created_at.asc())
        )
        all_prompts = prompts_result.scalars().all()

        available_versions = [
            {"version_name": p.version_name, "description": p.description, "is_default": p.is_default}
            for p in all_prompts
        ]

        return success_response({
            "tool_id": tool.id,
            "spider_name": tool.spider_name,
            "current_version": None,
            "current_description": default_prompt.description if default_prompt else None,
            "available_versions": available_versions,
        }, "工具提示词版本已恢复默认")


# ========== Spider Info Endpoints ==========


@router.get("/spiders/available")
async def list_available_spiders():
    """列出所有可用于 MCP 服务的 Spider"""
    spider_reg = get_spider_register()
    spider_info = spider_reg.list_spider_info()

    responses = []
    for info in spider_info:
        spider = spider_reg.get_spider_instance(info["name"])

        parameter_info = []
        has_params_model = False
        if spider and spider.params_model:
            has_params_model = True
            parameter_info = extract_parameter_info(spider.params_model)

        responses.append({
            "name": info["name"],
            "description": info.get("description", ""),
            "platform": info.get("platform", ""),
            "version": info.get("version", ""),
            "has_params_model": has_params_model,
            "parameter_info": parameter_info,
        })

    return success_response(responses, "获取可用 Spider 列表成功")


# ========== Helper Functions ==========


async def _get_active_tool_prompt(session, tool: MCPTool) -> SpiderPrompt | None:
    """获取工具实际使用的提示词版本"""
    if tool.selected_prompt_version:
        # 使用指定版本
        result = await session.execute(
            select(SpiderPrompt).where(
                SpiderPrompt.spider_name == tool.spider_name,
                SpiderPrompt.version_name == tool.selected_prompt_version
            )
        )
        return result.scalar_one_or_none()
    else:
        # 使用默认版本
        result = await session.execute(
            select(SpiderPrompt).where(
                SpiderPrompt.spider_name == tool.spider_name,
                SpiderPrompt.is_default == True
            )
        )
        return result.scalar_one_or_none()


async def _ensure_default_spider_prompt(session, spider_name: str, spider) -> SpiderPrompt:
    """确保 Spider 有默认提示词版本"""
    result = await session.execute(
        select(SpiderPrompt).where(
            SpiderPrompt.spider_name == spider_name,
            SpiderPrompt.is_default == True
        )
    )
    default = result.scalar_one_or_none()

    if not default:
        default = SpiderPrompt(
            spider_name=spider_name,
            version_name="默认",
            description=generate_tool_description(spider),
            is_default=True
        )
        session.add(default)
        await session.flush()

    return default
