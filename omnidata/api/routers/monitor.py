"""
系统监控路由
"""

import logging
import os
import time
from datetime import datetime

from fastapi import APIRouter
from psutil import Process

from omnidata.api.responses import success_response, error_response
from omnidata.core import get_browser_context_pool
from omnidata.utils import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])

# 应用启动时间
_start_time = time.time()


@router.get("/browser-pool")
async def get_browser_pool_stats():
    """
    获取浏览器池状态

    Returns:
        浏览器池统计信息
    """
    try:
        pool = get_browser_context_pool()
        stats = pool.get_stats()

        return success_response(stats, "获取浏览器池状态成功")
    except Exception as e:
        logger.error(f"Error getting browser pool stats: {e}")
        return error_response(f"获取浏览器池状态失败: {str(e)}")


@router.get("/context-pool")
async def get_context_pool_stats():
    """
    获取 Context Pool 状态

    Returns:
        Context Pool 统计信息
    """
    try:
        pool = get_browser_context_pool()
        stats = pool.get_stats()

        return success_response(stats, "获取 Context Pool 状态成功")
    except Exception as e:
        logger.error(f"Error getting context pool stats: {e}")
        return error_response(f"获取 Context Pool 状态失败: {str(e)}")


@router.get("/performance")
async def get_performance_metrics():
    """
    获取性能指标

    Returns:
        性能指标信息
    """
    try:
        pool = get_browser_context_pool()
        stats = pool.get_stats()

        # 提取关键性能指标
        performance = {
            "browser": {
                "browser_count": stats.get("browser_count", 0),
            },
            "context": {
                "total_contexts": stats.get("context_count", 0),
                "reuse_rate": stats.get("reuse_rate", 0),
                "total_contexts_created": stats.get("total_contexts_created", 0),
                "total_contexts_reused": stats.get("total_contexts_reused", 0),
                "total_contexts_evicted": stats.get("total_contexts_evicted", 0),
            },
            "health": {
                "total_contexts_closed": stats.get("total_contexts_closed", 0),
            },
        }

        return success_response(performance, "获取性能指标成功")
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return error_response(f"获取性能指标失败: {str(e)}")



@router.get("/system")
async def get_system_stats():
    """
    获取系统资源状态

    Returns:
        系统资源信息
    """
    try:
        # 获取当前进程
        process = Process(os.getpid())
        memory_info = process.memory_info()

        # Redis 连接状态
        redis_connected = False
        try:
            redis = await get_redis()
            await redis.ping()
            redis_connected = True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")

        # 运行时间
        uptime = time.time() - _start_time

        return success_response(
            {
                "status": "healthy",
                "uptime_seconds": round(uptime, 2),
                "memory_usage_mb": round(memory_info.rss / 1024 / 1024, 2),
                "memory_percent": round(process.memory_percent(), 2),
                "cpu_percent": round(process.cpu_percent(), 2),
                "redis_connected": redis_connected,
                "timestamp": datetime.now().isoformat(),
            },
            "获取系统状态成功",
        )
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return error_response(f"获取系统状态失败: {str(e)}")


@router.get("/contexts")
async def get_contexts_list():
    """
    获取当前所有 Context 的详细信息

    Returns:
        Context 列表信息
    """
    try:
        pool = get_browser_context_pool()
        contexts = pool.get_contexts()

        return success_response(contexts, "获取 Context 列表成功")
    except Exception as e:
        logger.error(f"Error getting contexts list: {e}")
        return error_response(f"获取 Context 列表失败: {str(e)}")
