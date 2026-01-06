"""
API 中间件模块
"""

from omnidata.api.middleware.auth import ApiKeyMiddleware

__all__ = ["ApiKeyMiddleware"]
