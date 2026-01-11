"""
健康检查路由
"""

from fastapi import APIRouter

from omnidata.api.responses import success_response

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return success_response({"status": "healthy", "service": "omnidata"}, "服务正常")
