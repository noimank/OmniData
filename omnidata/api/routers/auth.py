"""
API KEY 认证路由
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from omnidata.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class VerifyRequest(BaseModel):
    """API KEY 验证请求"""

    api_key: str = Field(..., description="API KEY")


class VerifyResponse(BaseModel):
    """API KEY 验证响应"""

    valid: bool
    message: str
    required: bool


@router.post("/verify")
async def verify_api_key(request: VerifyRequest):
    """
    验证 API KEY

    Args:
        request: 包含 api_key 的请求体

    Returns:
        验证结果
    """
    # 检查是否配置了 API KEY
    configured_key = settings.auth.api_key

    if not configured_key:
        # 未配置 API KEY，直接通过
        return VerifyResponse(
            valid=True, message="系统未配置 API KEY，无需验证", required=False
        )

    # 验证 API KEY
    if request.api_key == configured_key:
        return VerifyResponse(valid=True, message="API KEY 验证成功", required=True)
    else:
        return VerifyResponse(valid=False, message="API KEY 验证失败", required=True)


@router.get("/config")
async def get_auth_config():
    """
    获取认证配置（用于前端检测是否需要 API KEY）

    Returns:
        认证配置信息
    """
    # 返回是否需要 API KEY（不返回具体的 KEY 值）
    return {
        "required": settings.auth.api_key is not None,
        "configured": settings.auth.api_key is not None,
    }
