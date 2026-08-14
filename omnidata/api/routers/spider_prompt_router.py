"""
Spider 提示词管理路由

提供爬虫级别的提示词版本管理功能。
每个 Spider 可以有多个版本的提示词，默认版本自动创建且不可删除。
"""

import logging

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update

from omnidata.api.responses import error_response, success_response
from omnidata.core.spider_register import get_spider_register
from omnidata.database import get_db_session
from omnidata.database.models import MCPTool, SpiderPrompt, MCPService
from omnidata.utils.mcp_utils import (
    ensure_default_spider_prompt,
    extract_parameter_info,
    generate_tool_description,
    get_active_tool_prompt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spider-prompts", tags=["spider-prompts"])


# ========== Request Models ==========


class SpiderPromptCreate(BaseModel):
    """创建 Spider 提示词请求"""

    spider_name: str = Field(..., description="Spider 名称", min_length=1, max_length=200)
    version_name: str = Field(..., description="版本名称", min_length=1, max_length=100)
    description: str = Field(..., description="提示词内容", min_length=1, max_length=5000)
    is_default: bool = Field(False, description="是否为默认版本（不可删除）")


class SpiderPromptUpdate(BaseModel):
    """更新 Spider 提示词请求"""

    version_name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1, max_length=5000)


class ToolPromptVersionUpdate(BaseModel):
    """设置工具提示词版本请求"""

    version_name: str = Field(..., description="要使用的提示词版本名称")


# ========== Spider Prompt CRUD Endpoints ==========


@router.get("")
async def list_spider_prompts(
    spider_name: str | None = None,
    is_default: bool | None = None,
):
    """列出所有 Spider 提示词版本

    支持按 spider_name 和 is_default 过滤。
    """
    async with get_db_session() as session:
        query = select(SpiderPrompt)
        if spider_name is not None:
            query = query.where(SpiderPrompt.spider_name == spider_name)
        if is_default is not None:
            query = query.where(SpiderPrompt.is_default == is_default)

        result = await session.execute(
            query.order_by(SpiderPrompt.is_default.desc(), SpiderPrompt.created_at.desc())
        )
        prompts = result.scalars().all()

        # 获取每个提示词的使用次数
        responses = []
        for prompt in prompts:
            # 计算使用次数：selected_prompt_version 匹配或（为空且是默认版本）
            if prompt.is_default:
                # 默认版本：统计所有使用此 spider 且 selected_prompt_version 为空的工具
                usage_count_result = await session.execute(
                    select(func.count(MCPTool.id)).where(
                        MCPTool.spider_name == prompt.spider_name,
                        MCPTool.selected_prompt_version == None,
                    )
                )
            else:
                # 自定义版本：统计 selected_prompt_version 匹配的工具
                usage_count_result = await session.execute(
                    select(func.count(MCPTool.id)).where(
                        MCPTool.spider_name == prompt.spider_name,
                        MCPTool.selected_prompt_version == prompt.version_name,
                    )
                )
            usage_count = usage_count_result.scalar() or 0

            responses.append(
                {
                    "id": prompt.id,
                    "spider_name": prompt.spider_name,
                    "version_name": prompt.version_name,
                    "description": prompt.description,
                    "is_default": prompt.is_default,
                    "usage_count": usage_count,
                    "created_at": prompt.created_at,
                    "updated_at": prompt.updated_at,
                }
            )

        return success_response(data=responses)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_spider_prompt(request: SpiderPromptCreate):
    """创建新的 Spider 提示词版本"""
    async with get_db_session() as session:
        # 验证 Spider 存在
        spider_reg = get_spider_register()
        spider = spider_reg.get_spider_instance(request.spider_name)
        if not spider:
            return error_response(
                message=f"Spider '{request.spider_name}' not found",
            )

        # 检查同名版本是否已存在
        existing = await session.execute(
            select(SpiderPrompt).where(
                SpiderPrompt.spider_name == request.spider_name,
                SpiderPrompt.version_name == request.version_name,
            )
        )
        if existing.scalar_one_or_none():
            return error_response(
                message=f"Prompt version '{request.version_name}' already exists for spider '{request.spider_name}'",
            )

        # 如果设置为默认版本，需要先取消该 Spider 的其他默认版本
        if request.is_default:
            await session.execute(
                update(SpiderPrompt)
                .where(
                    SpiderPrompt.spider_name == request.spider_name, SpiderPrompt.is_default == True
                )
                .values(is_default=False)
            )

        prompt = SpiderPrompt(
            spider_name=request.spider_name,
            version_name=request.version_name,
            description=request.description,
            is_default=request.is_default,
        )
        session.add(prompt)
        await session.commit()
        await session.refresh(prompt)

        response_data = {
            "id": prompt.id,
            "spider_name": prompt.spider_name,
            "version_name": prompt.version_name,
            "description": prompt.description,
            "is_default": prompt.is_default,
            "usage_count": 0,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
        }
        return success_response(
            data=response_data,
            message="Spider prompt created successfully",
        )


@router.get("/{prompt_id}")
async def get_spider_prompt(prompt_id: int):
    """获取指定提示词的详细信息"""
    async with get_db_session() as session:
        result = await session.execute(select(SpiderPrompt).where(SpiderPrompt.id == prompt_id))
        prompt = result.scalar_one_or_none()

        if not prompt:
            return error_response(
                message="Spider prompt not found",
            )

        # 获取使用次数
        if prompt.is_default:
            usage_count_result = await session.execute(
                select(func.count(MCPTool.id)).where(
                    MCPTool.spider_name == prompt.spider_name,
                    MCPTool.selected_prompt_version == None,
                )
            )
        else:
            usage_count_result = await session.execute(
                select(func.count(MCPTool.id)).where(
                    MCPTool.spider_name == prompt.spider_name,
                    MCPTool.selected_prompt_version == prompt.version_name,
                )
            )
        usage_count = usage_count_result.scalar() or 0

        response_data = {
            "id": prompt.id,
            "spider_name": prompt.spider_name,
            "version_name": prompt.version_name,
            "description": prompt.description,
            "is_default": prompt.is_default,
            "usage_count": usage_count,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
        }
        return success_response(data=response_data)


@router.put("/{prompt_id}")
async def update_spider_prompt(prompt_id: int, request: SpiderPromptUpdate):
    """更新 Spider 提示词"""
    async with get_db_session() as session:
        result = await session.execute(select(SpiderPrompt).where(SpiderPrompt.id == prompt_id))
        prompt = result.scalar_one_or_none()

        if not prompt:
            return error_response(
                message="Spider prompt not found",
            )

        # 如果修改版本名称，检查是否冲突
        if request.version_name and request.version_name != prompt.version_name:
            existing = await session.execute(
                select(SpiderPrompt).where(
                    SpiderPrompt.spider_name == prompt.spider_name,
                    SpiderPrompt.version_name == request.version_name,
                    SpiderPrompt.id != prompt_id,
                )
            )
            if existing.scalar_one_or_none():
                return error_response(
                    message=f"Prompt version '{request.version_name}' already exists for spider '{prompt.spider_name}'",
                )

        # 更新字段
        if request.version_name is not None:
            prompt.version_name = request.version_name
        if request.description is not None:
            prompt.description = request.description

        await session.commit()
        await session.refresh(prompt)

        # 获取使用次数
        if prompt.is_default:
            usage_count_result = await session.execute(
                select(func.count(MCPTool.id)).where(
                    MCPTool.spider_name == prompt.spider_name,
                    MCPTool.selected_prompt_version == None,
                )
            )
        else:
            usage_count_result = await session.execute(
                select(func.count(MCPTool.id)).where(
                    MCPTool.spider_name == prompt.spider_name,
                    MCPTool.selected_prompt_version == prompt.version_name,
                )
            )
        usage_count = usage_count_result.scalar() or 0

        response_data = {
            "id": prompt.id,
            "spider_name": prompt.spider_name,
            "version_name": prompt.version_name,
            "description": prompt.description,
            "is_default": prompt.is_default,
            "usage_count": usage_count,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
        }
        return success_response(
            data=response_data,
            message="Spider prompt updated successfully",
        )


@router.delete("/{prompt_id}")
async def delete_spider_prompt(prompt_id: int):
    """删除 Spider 提示词（默认版本或被使用的版本不可删除）"""
    async with get_db_session() as session:
        result = await session.execute(select(SpiderPrompt).where(SpiderPrompt.id == prompt_id))
        prompt = result.scalar_one_or_none()

        if not prompt:
            return error_response(
                message="Spider prompt not found",
            )

        # 默认版本不可删除
        if prompt.is_default:
            return error_response(
                message="Cannot delete default prompt version",
            )

        # 检查是否被工具使用
        usage_count_result = await session.execute(
            select(func.count(MCPTool.id)).where(
                MCPTool.spider_name == prompt.spider_name,
                MCPTool.selected_prompt_version == prompt.version_name,
            )
        )
        usage_count = usage_count_result.scalar() or 0
        if usage_count > 0:
            return error_response(
                message=f"Prompt version is used by {usage_count} tool(s). Remove associations first.",
            )

        await session.execute(delete(SpiderPrompt).where(SpiderPrompt.id == prompt_id))
        await session.commit()

        return success_response(
            data=None,
            message="Spider prompt deleted successfully",
        )


@router.put("/{prompt_id}/set-default")
async def set_prompt_as_default(prompt_id: int):
    """将指定提示词版本设为默认版本

    新创建的 MCP 服务将使用新的默认版本。
    """
    async with get_db_session() as session:
        # 验证提示词存在
        result = await session.execute(select(SpiderPrompt).where(SpiderPrompt.id == prompt_id))
        prompt = result.scalar_one_or_none()

        if not prompt:
            return error_response(
                message="Spider prompt not found",
            )

        # 如果已是默认版本，直接返回
        if prompt.is_default:
            # 获取使用次数
            usage_count_result = await session.execute(
                select(func.count(MCPTool.id)).where(
                    MCPTool.spider_name == prompt.spider_name,
                    MCPTool.selected_prompt_version == None,
                )
            )
            usage_count = usage_count_result.scalar() or 0

            response_data = {
                "id": prompt.id,
                "spider_name": prompt.spider_name,
                "version_name": prompt.version_name,
                "description": prompt.description,
                "is_default": prompt.is_default,
                "usage_count": usage_count,
                "created_at": prompt.created_at,
                "updated_at": prompt.updated_at,
            }
            return success_response(
                data=response_data,
                message="Prompt is already the default version",
            )

        spider_name = prompt.spider_name

        # 数据库事务：将该 Spider 的所有提示词 is_default 设为 False，目标提示词设为 True
        await session.execute(
            update(SpiderPrompt)
            .where(SpiderPrompt.spider_name == spider_name, SpiderPrompt.is_default == True)
            .values(is_default=False)
        )
        prompt.is_default = True
        await session.commit()
        await session.refresh(prompt)

        # 获取使用次数
        usage_count_result = await session.execute(
            select(func.count(MCPTool.id)).where(
                MCPTool.spider_name == spider_name, MCPTool.selected_prompt_version == None
            )
        )
        usage_count = usage_count_result.scalar() or 0

        response_data = {
            "id": prompt.id,
            "spider_name": prompt.spider_name,
            "version_name": prompt.version_name,
            "description": prompt.description,
            "is_default": prompt.is_default,
            "usage_count": usage_count,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
        }

        return success_response(
            data=response_data,
            message="Spider prompt set as default successfully",
        )


@router.get("/{prompt_id}/usage")
async def get_prompt_usage(prompt_id: int):
    """查询提示词被哪些工具使用"""
    async with get_db_session() as session:
        result = await session.execute(select(SpiderPrompt).where(SpiderPrompt.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if not prompt:
            return error_response(
                message="Spider prompt not found",
            )

        # 查找使用此提示词版本的工具
        if prompt.is_default:
            # 默认版本：查找所有使用该 spider 且 selected_prompt_version 为空的工具
            tools_result = await session.execute(
                select(MCPTool, MCPService)
                .join(MCPService, MCPTool.service_id == MCPService.id)
                .where(
                    MCPTool.spider_name == prompt.spider_name,
                    MCPTool.selected_prompt_version == None,
                )
            )
        else:
            # 自定义版本：查找 selected_prompt_version 匹配的工具
            tools_result = await session.execute(
                select(MCPTool, MCPService)
                .join(MCPService, MCPTool.service_id == MCPService.id)
                .where(
                    MCPTool.spider_name == prompt.spider_name,
                    MCPTool.selected_prompt_version == prompt.version_name,
                )
            )

        tools = []
        for tool, service in tools_result.all():
            tools.append(
                {
                    "tool_id": tool.id,
                    "tool_name": tool.tool_name,
                    "service_id": service.id,
                    "service_name": service.name,
                    "service_display_name": service.display_name,
                }
            )

        response_data = {
            "prompt_id": prompt_id,
            "spider_name": prompt.spider_name,
            "version_name": prompt.version_name,
            "usage_count": len(tools),
            "tools": tools,
        }
        return success_response(data=response_data)


# ========== Per-Spider Prompt Endpoints ==========


@router.get("/spiders/{spider_name}/prompts")
async def list_spider_prompts_by_name(spider_name: str):
    """获取指定 Spider 的所有提示词版本"""
    async with get_db_session() as session:
        # 验证 Spider 存在
        spider_reg = get_spider_register()
        spider = spider_reg.get_spider_instance(spider_name)
        if not spider:
            return error_response(
                message=f"Spider '{spider_name}' not found",
            )

        result = await session.execute(
            select(SpiderPrompt)
            .where(SpiderPrompt.spider_name == spider_name)
            .order_by(SpiderPrompt.is_default.desc(), SpiderPrompt.created_at.desc())
        )
        prompts = result.scalars().all()

        responses = []
        for prompt in prompts:
            if prompt.is_default:
                usage_count_result = await session.execute(
                    select(func.count(MCPTool.id)).where(
                        MCPTool.spider_name == spider_name, MCPTool.selected_prompt_version == None
                    )
                )
            else:
                usage_count_result = await session.execute(
                    select(func.count(MCPTool.id)).where(
                        MCPTool.spider_name == spider_name,
                        MCPTool.selected_prompt_version == prompt.version_name,
                    )
                )
            usage_count = usage_count_result.scalar() or 0

            responses.append(
                {
                    "id": prompt.id,
                    "spider_name": prompt.spider_name,
                    "version_name": prompt.version_name,
                    "description": prompt.description,
                    "is_default": prompt.is_default,
                    "usage_count": usage_count,
                    "created_at": prompt.created_at,
                    "updated_at": prompt.updated_at,
                }
            )

        return success_response(data=responses)


@router.post("/spiders/{spider_name}/prompts", status_code=status.HTTP_201_CREATED)
async def create_spider_prompt_for_spider(spider_name: str, request: SpiderPromptCreate):
    """为指定 Spider 创建提示词版本（spider_name 从路径获取）"""
    async with get_db_session() as session:
        # 验证 Spider 存在
        spider_reg = get_spider_register()
        spider = spider_reg.get_spider_instance(spider_name)
        if not spider:
            return error_response(
                message=f"Spider '{spider_name}' not found",
            )

        # 检查同名版本是否已存在
        existing = await session.execute(
            select(SpiderPrompt).where(
                SpiderPrompt.spider_name == spider_name,
                SpiderPrompt.version_name == request.version_name,
            )
        )
        if existing.scalar_one_or_none():
            return error_response(
                message=f"Prompt version '{request.version_name}' already exists for spider '{spider_name}'",
            )

        # 如果设置为默认版本，需要先取消该 Spider 的其他默认版本
        if request.is_default:
            await session.execute(
                update(SpiderPrompt)
                .where(SpiderPrompt.spider_name == spider_name, SpiderPrompt.is_default == True)
                .values(is_default=False)
            )

        prompt = SpiderPrompt(
            spider_name=spider_name,
            version_name=request.version_name,
            description=request.description,
            is_default=request.is_default,
        )
        session.add(prompt)
        await session.commit()
        await session.refresh(prompt)

        response_data = {
            "id": prompt.id,
            "spider_name": prompt.spider_name,
            "version_name": prompt.version_name,
            "description": prompt.description,
            "is_default": prompt.is_default,
            "usage_count": 0,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
        }
        return success_response(
            data=response_data,
            message="Spider prompt created successfully",
        )


@router.get("/spiders/{spider_name}/default-prompt")
async def get_spider_default_prompt(spider_name: str):
    """获取指定 Spider 的默认提示词版本"""
    async with get_db_session() as session:
        # 验证 Spider 存在
        spider_reg = get_spider_register()
        spider = spider_reg.get_spider_instance(spider_name)
        if not spider:
            return error_response(
                message=f"Spider '{spider_name}' not found",
            )

        result = await session.execute(
            select(SpiderPrompt).where(
                SpiderPrompt.spider_name == spider_name, SpiderPrompt.is_default == True
            )
        )
        prompt = result.scalar_one_or_none()

        if not prompt:
            # 如果不存在默认版本，自动创建
            prompt = SpiderPrompt(
                spider_name=spider_name,
                version_name="默认",
                description=generate_tool_description(spider),
                is_default=True,
            )
            session.add(prompt)
            await session.commit()
            await session.refresh(prompt)

        # 获取使用次数
        usage_count_result = await session.execute(
            select(func.count(MCPTool.id)).where(
                MCPTool.spider_name == spider_name, MCPTool.selected_prompt_version == None
            )
        )
        usage_count = usage_count_result.scalar() or 0

        response_data = {
            "id": prompt.id,
            "spider_name": prompt.spider_name,
            "version_name": prompt.version_name,
            "description": prompt.description,
            "is_default": prompt.is_default,
            "usage_count": usage_count,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
        }
        return success_response(data=response_data)


# ========== Spider Registry Endpoints ==========


@router.get("/spiders/available")
async def list_available_spiders():
    """列出所有可用于提示词管理的 Spider"""
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

        responses.append(
            {
                "name": info["name"],
                "description": info.get("description", ""),
                "platform": info.get("platform", ""),
                "version": info.get("version", ""),
                "has_params_model": has_params_model,
                "parameter_info": parameter_info,
            }
        )

    return success_response(data=responses)
