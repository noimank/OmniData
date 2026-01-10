"""
数据库会话管理
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from omnidata.core.config import settings
from omnidata.database.models import Base


# 数据库引擎和会话工厂
_engine = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


def _get_database_path() -> Path:
    """获取数据库文件路径"""
    db_path = settings.db.db_path
    path = Path(db_path)
    # 确保目录存在
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def init_db() -> None:
    """初始化数据库，创建所有表"""
    global _engine, async_session_maker

    db_path = _get_database_path()
    database_url = f"sqlite+aiosqlite:///{db_path.absolute()}"

    # 创建引擎
    _engine = create_async_engine(
        database_url,
        echo=False,  # 生产环境设置为 False
        pool_pre_ping=True,
    )

    # 为所有连接启用外键约束（SQLite 默认禁用外键约束）
    @event.listens_for(_engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # 创建会话工厂
    async_session_maker = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 创建所有表
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db_session():
    """获取数据库会话的上下文管理器"""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    """关闭数据库引擎，释放所有连接"""
    import asyncio

    global _engine, async_session_maker

    if _engine is not None:
        logger = logging.getLogger(__name__)
        try:
            await asyncio.wait_for(_engine.dispose(), timeout=3.0)
            logger.info("Database engine closed")
        except asyncio.TimeoutError:
            logger.warning("Database close timeout, proceeding with cleanup")
        except asyncio.CancelledError:
            logger.debug("Database close cancelled during shutdown")
        except Exception as e:
            logger.error(f"Error closing database engine: {e}")
        finally:
            _engine = None
            async_session_maker = None
