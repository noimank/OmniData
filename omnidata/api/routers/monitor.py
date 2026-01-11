"""
系统监控路由
"""

import logging
import os
import time
from datetime import datetime

from fastapi import APIRouter
from psutil import Process, virtual_memory

from omnidata.api.responses import success_response, error_response
from omnidata.core import get_browser_pool, spider_register
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
    from omnidata.core.config import settings

    try:
        pool = await get_browser_pool()
        stats = pool.get_stats()

        # 添加配置信息
        stats["config"] = {
            "pool_initial_size": settings.browser.pool_initial_size,
            "idle_timeout": settings.browser.idle_timeout,
            "headless": settings.browser.headless,
        }

        return success_response(stats, "获取浏览器池状态成功")
    except Exception as e:
        logger.error(f"Error getting browser pool stats: {e}")
        return error_response(f"获取浏览器池状态失败: {str(e)}")


@router.get("/spiders")
async def get_spider_stats():
    """
    获取爬虫统计信息

    Returns:
        爬虫统计信息
    """
    try:
        register = spider_register()
        spiders = register.list_spider_info()

        enabled_count = sum(1 for s in spiders if s.get("enabled", True))

        return success_response(
            {"total_count": len(spiders), "enabled_count": enabled_count, "spiders": spiders},
            "获取爬虫统计成功",
        )
    except Exception as e:
        logger.error(f"Error getting spider stats: {e}")
        return error_response(f"获取爬虫统计失败: {str(e)}")


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


@router.get("/stats")
async def get_all_stats():
    """
    获取综合统计信息

    Returns:
        综合统计信息
    """
    try:
        pool = await get_browser_pool()
        register = spider_register()

        # 系统状态
        process = Process(os.getpid())
        memory_info = process.memory_info()
        uptime = time.time() - _start_time

        # Redis 状态
        redis_connected = False
        try:
            redis = await get_redis()
            await redis.ping()
            redis_connected = True
        except Exception:
            pass

        return success_response(
            {
                "browser_pool": {
                    "browser_count": pool.browser_count,
                    "browsers": pool.get_stats()["browsers"],
                },
                "spiders": {
                    "total_count": register.spider_count,
                    "spiders": register.list_spider_info(),
                },
                "system": {
                    "status": "healthy",
                    "uptime_seconds": round(uptime, 2),
                    "memory_usage_mb": round(memory_info.rss / 1024 / 1024, 2),
                    "cpu_percent": round(process.cpu_percent(), 2),
                    "redis_connected": redis_connected,
                    "timestamp": datetime.now().isoformat(),
                },
            },
            "获取综合统计成功",
        )
    except Exception as e:
        logger.error(f"Error getting all stats: {e}")
        return error_response(f"获取综合统计失败: {str(e)}")
