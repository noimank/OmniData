"""
FastAPI 主应用模块
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from omnidata.core.mcp_manager import get_mcp_manager

from omnidata.api.routers import health, logins, mcp_services, monitor, spiders
from omnidata.api.routers.spider_prompt_router import router as spider_prompt_router
from omnidata.core import get_browser_pool, get_login_register, get_spider_register
from omnidata.database import init_db
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
        # 初始化数据库
        await init_db()
        logger.info("Database initialized")

        # 初始化浏览器池
        browser_pool = await get_browser_pool()
        logger.info("Browser pool initialized")

        # 初始化爬虫注册器
        spider_reg = await get_spider_register(browser_pool=browser_pool)
        logger.info(f"Spider register initialized with {spider_reg.spider_count} spiders")

        # 初始化登录注册器
        login_reg = await get_login_register(browser_pool=browser_pool)
        logger.info(f"Login register initialized with {login_reg.login_count} logins")

        # 恢复已激活的 MCP 服务
        from omnidata.database import get_db_session
        from omnidata.database.models import MCPService, SpiderPrompt
        from sqlalchemy import select, update
        from sqlalchemy.orm import selectinload

        async with get_db_session() as session:
            result = await session.execute(
                select(MCPService)
                .options(selectinload(MCPService.tools))
                .where(MCPService.is_active == True)
            )
            active_services = result.scalars().all()

            if active_services:
                logger.info(f"Restoring {len(active_services)} active MCP services...")
                mcp_manager = await get_mcp_manager()

                for service in active_services:
                    try:
                        # 获取服务的工具配置
                        spider_names = [t.spider_name for t in service.tools if t.enabled]
                        tool_configs = {}

                        for t in service.tools:
                            if not t.enabled:
                                continue

                            # 获取工具当前使用的提示词版本
                            if t.selected_prompt_version:
                                # 使用指定版本
                                prompt_result = await session.execute(
                                    select(SpiderPrompt).where(
                                        SpiderPrompt.spider_name == t.spider_name,
                                        SpiderPrompt.version_name == t.selected_prompt_version
                                    )
                                )
                            else:
                                # 使用默认版本
                                prompt_result = await session.execute(
                                    select(SpiderPrompt).where(
                                        SpiderPrompt.spider_name == t.spider_name,
                                        SpiderPrompt.is_default == True
                                    )
                                )

                            prompt = prompt_result.scalar_one_or_none()
                            description = prompt.description if prompt else ""

                            tool_configs[t.spider_name] = {
                                "tool_name": t.tool_name,
                                "description": description
                            }

                        # 重新挂载服务
                        await mcp_manager.mount_service(
                            service_name=service.name,
                            display_name=service.display_name,
                            description=service.description or "",
                            transport=service.transport,
                            spider_names=spider_names,
                            tool_configs=tool_configs,
                        )
                        logger.info(f"Restored MCP service: {service.name}")
                    except Exception as e:
                        logger.error(f"Failed to restore MCP service {service.name}: {e}, deactivating...")
                        # 自动停用服务以避免数据库与内存状态不一致
                        await session.execute(
                            update(MCPService)
                            .where(MCPService.id == service.id)
                            .values(is_active=False)
                        )
                        await session.commit()

        logger.info("OmniData application started successfully")

        yield
        # 应用关闭时清理
        logger.info("Shutting down OmniData application...")

    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise

    finally:
        # 关闭时清理（各关闭函数内部有超时保护）
        logger.info("Shutting down OmniData application...")

        # 阶段 1: 清理所有 MCP 服务
        try:
            mcp_manager = await get_mcp_manager()
            await mcp_manager.cleanup_all_services()
            logger.info("All MCP services cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up MCP services: {e}")

        from omnidata.core.browser_pool import close_browser_pool
        from omnidata.core.login_register import close_login_register
        from omnidata.core.spider_register import close_spider_register

        # 阶段 2: 关闭数据库（在其他组件清理前关闭，避免连接泄漏）
        from omnidata.database import close_db
        try:
            await close_db()
        except Exception as e:
            logger.error(f"Error closing database: {e}")

        # 阶段 3: 关闭登录器和爬虫注册器（串行执行，避免 CancelledError 传播）
        try:
            await close_login_register()
        except Exception as e:
            logger.error(f"Error closing login register: {e}")

        try:
            await close_spider_register()
        except Exception as e:
            logger.error(f"Error closing spider register: {e}")

        # 阶段 4: 关闭浏览器池
        try:
            await close_browser_pool()
        except Exception as e:
            logger.error(f"Error closing browser pool: {e}")

        # 阶段 5: 关闭 Redis
        try:
            await close_redis()
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

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
    expose_headers=[],
)

# 注册路由
app.include_router(health.router)
app.include_router(spiders.router)
app.include_router(monitor.router)
app.include_router(logins.router)
app.include_router(mcp_services.router)
app.include_router(spider_prompt_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "OmniData",
        "version": "0.1.0",
        "description": "A scalable web scraping framework",
        "docs": "/docs",
    }
