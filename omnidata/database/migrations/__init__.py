"""
数据库迁移模块

提供简单的迁移运行器，用于在开发环境中执行数据库结构变更。
"""

import asyncio
import logging

from omnidata.database import get_db_session, init_db

logger = logging.getLogger(__name__)

# 迁移注册表
MIGRATIONS = []


async def run_migrations() -> None:
    """运行所有待执行的迁移"""
    await init_db()

    async with get_db_session() as session:
        for migration_name, migration_func in MIGRATIONS:
            try:
                logger.info(f"Running migration: {migration_name}")
                await migration_func(session)
                logger.info(f"Migration {migration_name} completed")
            except Exception as e:
                logger.error(f"Migration {migration_name} failed: {e}")
                raise


if __name__ == "__main__":
    # 可以直接运行此文件来执行迁移
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migrations())
