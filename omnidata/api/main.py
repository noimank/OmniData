"""
FastAPI 主应用模块
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omnidata.api.middleware import ApiKeyMiddleware
from omnidata.api.routers import auth, health, logins, monitor, spiders
from omnidata.core import get_browser_pool, get_login_register, get_spider_register
from omnidata.utils import close_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    处理启动时的初始化和关闭时的清理
    """
    # 启动时初始化
    logger.info("Starting OmniData application...")

    try:
        # 初始化浏览器池
        browser_pool = await get_browser_pool()
        logger.info("Browser pool initialized")

        # 初始化爬虫注册器
        spider_reg = await get_spider_register(browser_pool=browser_pool)
        logger.info(f"Spider register initialized with {spider_reg.spider_count} spiders")

        # 初始化登录注册器
        login_reg = await get_login_register(browser_pool=browser_pool)
        logger.info(f"Login register initialized with {login_reg.login_count} logins")

        logger.info("OmniData application started successfully")

        yield

    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise

    finally:
        # 关闭时清理
        logger.info("Shutting down OmniData application...")

        from omnidata.core.browser_pool import close_browser_pool
        from omnidata.core.login_register import close_login_register
        from omnidata.core.spider_register import close_spider_register

        await close_login_register()
        await close_spider_register()
        await close_browser_pool()
        await close_redis()

        logger.info("OmniData application shut down")


# 创建 FastAPI 应用
app = FastAPI(
    title="OmniData",
    description="A scalable web scraping framework with Playwright and FastAPI",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-API-Key"],
)

# 添加 API KEY 验证中间件
app.add_middleware(ApiKeyMiddleware)

# 注册路由
app.include_router(health.router)
app.include_router(spiders.router)
app.include_router(monitor.router)
app.include_router(logins.router)
app.include_router(auth.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "OmniData",
        "version": "0.1.0",
        "description": "A scalable web scraping framework",
        "docs": "/docs",
    }
