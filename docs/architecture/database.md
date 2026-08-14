# 数据库设计

OmniData 使用 SQLite 存储 MCP 服务配置、提示词版本和审计日志。

---

## 数据库技术栈

- **ORM**：SQLAlchemy 2.0+
- **驱动**：aiosqlite（异步 SQLite）
- **数据库文件**：`data/omnidata.db`（随项目目录自动创建，容器部署建议挂载）

---

## 数据表

### 1. spider_prompt

爬虫级提示词版本（全系统共享）。每个 Spider 可有多个版本，默认版本自动创建且不可删除，工具可选择指定版本，为空则使用默认版本。

```sql
CREATE TABLE spider_prompt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spider_name VARCHAR(200) NOT NULL,          -- 关联的 Spider 名称（带索引）
    version_name VARCHAR(100) NOT NULL,          -- 版本名称（如：默认、详细版）
    description TEXT NOT NULL,                   -- 提示词内容
    is_default BOOLEAN NOT NULL DEFAULT false,   -- 是否为默认版本（不可删除）
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (spider_name, version_name)
);
```

### 2. mcp_service

MCP 服务配置。

```sql
CREATE TABLE mcp_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,           -- 服务名称（用于路由，唯一）
    display_name VARCHAR(200) NOT NULL,          -- 显示名称
    description TEXT,
    transport VARCHAR(50) NOT NULL DEFAULT 'http',  -- http/streamable-http/sse
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 3. mcp_tool

MCP 工具表，关联 Spider 到服务。每个工具通过 `selected_prompt_version` 选择使用哪个版本的 `spider_prompt`（为空则使用默认版本）。

```sql
CREATE TABLE mcp_tool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL REFERENCES mcp_service(id) ON DELETE CASCADE,
    spider_name VARCHAR(200) NOT NULL,           -- 关联的 Spider
    tool_name VARCHAR(200) NOT NULL,             -- 自定义工具名称
    enabled BOOLEAN NOT NULL DEFAULT true,
    selected_prompt_version VARCHAR(100),        -- 指定提示词版本（为空用默认）
    UNIQUE (service_id, spider_name)
);
```

### 4. spider_audit

爬虫调用审计记录，记录每次爬虫调用的详细信息。

```sql
CREATE TABLE spider_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spider_name VARCHAR(200) NOT NULL,           -- 爬虫名称（带索引）
    platform VARCHAR(100) NOT NULL,              -- 平台名称（带索引）
    spider_version VARCHAR(50) NOT NULL,         -- 爬虫版本
    success BOOLEAN NOT NULL,                    -- 执行是否成功（带索引）
    error_message TEXT,                          -- 错误信息
    started_at DATETIME NOT NULL,                -- 开始时间（带索引）
    completed_at DATETIME,                       -- 完成时间
    duration_seconds FLOAT NOT NULL,             -- 执行时长（秒）
    params TEXT,                                 -- 爬虫参数（JSON）
    result_metadata TEXT,                        -- 返回元数据（JSON）
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## ORM 使用

所有数据库操作均为 SQLAlchemy 2.0 异步会话方式：

```python
from sqlalchemy import select
from omnidata.database import get_db_session
from omnidata.database.models import SpiderAudit

# 查询最近的审计记录
async with get_db_session() as session:
    result = await session.execute(
        select(SpiderAudit)
        .where(SpiderAudit.spider_name == "eastmoney_stock_quote")
        .order_by(SpiderAudit.created_at.desc())
        .limit(10)
    )
    audits = result.scalars().all()
```

---

## 审计 API

### 统计数据

```bash
GET /api/v1/spider-audit/stats
```

### 查询记录

```bash
GET /api/v1/spider-audit/records?spider_name=eastmoney_stock_quote&limit=10
```

### 清理旧数据

```bash
DELETE /api/v1/spider-audit/cleanup?days=30
```

### 批量删除记录

```bash
DELETE /api/v1/spider-audit/records/batch
```

---

## 数据备份

```bash
# 备份数据库
cp data/omnidata.db data/omnidata.db.backup.$(date +%Y%m%d)

# 或使用 SQLite 导出
sqlite3 data/omnidata.db .dump > backup.sql
```

---

## 配置

数据库路径为固定值 `data/omnidata.db`，随项目目录创建，不通过环境变量配置。
容器部署时挂载 `/app/data` 目录即可持久化（见 [部署指南](../development/deployment.md)）。

---

详见：
- [系统架构概览](overview.md)
- [监控 API](../api/monitoring.md)
