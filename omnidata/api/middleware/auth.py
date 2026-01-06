"""
API KEY 认证中间件
"""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from omnidata.core.config import settings

logger = logging.getLogger(__name__)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """
    API KEY 验证中间件

    当配置了 OMNIDATA_AUTH__API_KEY 时，对除以下路径外的所有请求进行 API KEY 验证：
    - / (根路径)
    - /docs (API 文档)
    - /openapi.json (OpenAPI 规范)
    - /redoc (ReDoc 文档)
    - /health (健康检查)
    - /api/v1/auth (认证相关接口)
    """

    # 不需要验证的路径前缀
    EXEMPT_PATHS = {
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
        "/api/v1/auth",
    }

    async def dispatch(self, request: Request, call_next):
        """
        处理请求

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象
        """
        # 检查是否配置了 API KEY
        configured_key = settings.auth.api_key
        if not configured_key:
            # 未配置 API KEY，直接放行
            return await call_next(request)

        # 豁免 OPTIONS 预检请求（浏览器不会在 OPTIONS 请求中携带自定义请求头）
        if request.method == "OPTIONS":
            return await call_next(request)

        # 检查路径是否在豁免列表中
        if any(
            request.url.path == exempt_path or request.url.path.startswith(exempt_path + "/")
            for exempt_path in self.EXEMPT_PATHS
        ):
            return await call_next(request)

        # 从请求头获取 API KEY
        api_key = request.headers.get("x-api-key")

        # 验证 API KEY
        if api_key != configured_key:
            logger.warning(
                f"Invalid API KEY attempt from {request.client.host} to {request.url.path}. "
                f"Received: {api_key[:10] if api_key else 'None'}..."
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing API KEY"},
            )

        # 验证通过，继续处理请求
        return await call_next(request)
