"""
工具模块
"""

from .redis_client import close_redis, get_redis

__all__ = [
    "get_redis",
    "close_redis",
]
