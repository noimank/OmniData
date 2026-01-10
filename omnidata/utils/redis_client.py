"""
Redis 客户端模块
"""

import asyncio
import logging

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from omnidata.core.config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None
_pool: ConnectionPool | None = None
_lock: "asyncio.Lock" = None


async def get_redis() -> Redis:
    """
    获取 Redis 客户端实例

    Returns:
        Redis: Redis 客户端实例
    """
    global _redis, _pool, _lock

    if _lock is None:
        _lock = asyncio.Lock()

    async with _lock:
        if _redis is None:
            await _init_redis()

        return _redis


async def _init_redis() -> None:
    """初始化 Redis 连接"""
    global _redis, _pool

    redis_config = settings.redis

    _pool = ConnectionPool(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        max_connections=redis_config.max_connections,
        socket_timeout=redis_config.socket_timeout,
        socket_connect_timeout=redis_config.socket_connect_timeout,
        decode_responses=redis_config.decode_responses,
    )

    _redis = Redis(connection_pool=_pool)

    try:
        await _redis.ping()
        logger.info(f"Redis connected: {redis_config.host}:{redis_config.port}")
    except RedisError as e:
        logger.error(f"Redis connection failed: {e}")
        raise


async def close_redis() -> None:
    """关闭 Redis 连接（带超时保护）"""
    global _redis, _pool

    # 关闭 Redis 客户端
    if _redis is not None:
        try:
            await asyncio.wait_for(_redis.aclose(), timeout=3.0)
            logger.info("Redis connection closed")
        except asyncio.TimeoutError:
            logger.warning("Redis close timeout, proceeding with cleanup")
        except asyncio.CancelledError:
            logger.debug("Redis close cancelled during shutdown")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")
        finally:
            _redis = None

    # 断开连接池
    if _pool is not None:
        try:
            await asyncio.wait_for(_pool.disconnect(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("Redis pool disconnect timeout, proceeding with cleanup")
        except asyncio.CancelledError:
            logger.debug("Redis pool disconnect cancelled during shutdown")
        except Exception as e:
            logger.error(f"Error disconnecting Redis pool: {e}")
        finally:
            _pool = None
