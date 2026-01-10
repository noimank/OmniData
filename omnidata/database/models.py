"""
数据库模型
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


# ========== Spider 提示词（全系统共享） ==========


class SpiderPrompt(Base):
    """爬虫级别的提示词版本（全系统共享）

    每个 Spider 可以有多个版本的提示词，默认版本自动创建且不可删除。
    工具可以选择使用特定版本，为空则使用该 Spider 的默认版本。
    """

    __tablename__ = "spider_prompt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spider_name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="关联的 Spider 名称"
    )
    version_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="版本名称（如：默认、详细版、简洁版）"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="提示词内容")
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否为默认版本（不可删除）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # 索引和约束
    __table_args__ = (
        UniqueConstraint("spider_name", "version_name", name="uq_spider_prompt_version"),
    )


# ========== MCP 服务和工具 ==========


class MCPService(Base):
    """MCP 服务表"""

    __tablename__ = "mcp_service"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    transport: Mapped[str] = mapped_column(
        String(50), nullable=False, default="http"
    )  # http, streamable-http, sse
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # 关系
    tools: Mapped[list["MCPTool"]] = relationship(
        "MCPTool", back_populates="service", cascade="all, delete-orphan"
    )


class MCPTool(Base):
    """MCP 工具表（关联 Spider 到服务）

    每个 Tool 通过 selected_prompt_version 字段选择使用哪个版本的 SpiderPrompt。
    如果 selected_prompt_version 为空，则使用该 Spider 的默认提示词版本。
    """

    __tablename__ = "mcp_tool"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mcp_service.id", ondelete="CASCADE"), nullable=False
    )
    spider_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)  # 自定义工具名称
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 新增：指定使用的提示词版本（为空表示使用默认版本）
    selected_prompt_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="指定的提示词版本名称（为空则使用默认版本）"
    )

    # 关系
    service: Mapped["MCPService"] = relationship("MCPService", back_populates="tools")

    # 约束：防止同一个服务中添加重复的 spider
    __table_args__ = (
        UniqueConstraint("service_id", "spider_name", name="uq_mcp_tool_service_spider"),
    )
