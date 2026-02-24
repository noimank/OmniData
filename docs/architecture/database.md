# 数据库设计

OmniData 使用 SQLite 存储审计日志和配置数据。

---

## 数据库技术栈

- **ORM**：SQLAlchemy 2.0+
- **驱动**：aiosqlite（异步 SQLite）
- **数据库文件**：`omnidata.db`

---

## 数据表

### 1. spider_audit

爬虫执行审计日志。

```sql
CREATE TABLE spider_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spider_name VARCHAR(100) NOT NULL,
    params TEXT,                    -- JSON 格式的请求参数
    status VARCHAR(20) NOT NULL,    -- success/failed
    execution_time FLOAT,           -- 执行耗时（秒）
    error_message TEXT,             -- 错误信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_spider_name (spider_name),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
);
```

### 2. mcp_services

MCP 服务配置。

```sql
CREATE TABLE mcp_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    spider_names TEXT NOT NULL,     -- JSON 数组
    transport VARCHAR(20) NOT NULL, -- http/streamable-http/sse
    tool_prompts TEXT,              -- JSON 对象，工具提示词
    enabled BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3. login_state

登录状态记录（可选，主要使用 Redis）。

```sql
CREATE TABLE login_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform VARCHAR(50) NOT NULL,
    namespace VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,    -- pending/success/expired
    qr_data TEXT,                   -- 二维码数据
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (platform, namespace)
);
```

---

## ORM 模型

### SpiderAudit

```python
from omnidata.database.models import SpiderAudit

# 创建记录
await SpiderAudit.create(
    spider_name="eastmoney_stock_quote",
    params={"secucode": "000001"},
    status="success",
    execution_time=1.23
)

# 查询统计
stats = await SpiderAudit.get_stats()
```

### MCPService

```python
from omnidata.database.models import MCPService

# 创建服务
service = await MCPService.create(
    name="financial-data",
    description="金融数据服务",
    spider_names=["eastmoney_stock_quote"],
    transport="streamable-http"
)

# 获取服务
service = await MCPService.get_by_name("financial-data")
```

---

## 数据库操作

### 会话管理

```python
from omnidata.database.session import get_session

async with get_session() as session:
    # 使用 session 执行操作
    result = await session.execute(select(SpiderAudit))
    audits = result.scalars().all()
```

### 异步执行

所有数据库操作都是异步的：

```python
# 查询
audits = await SpiderAudit.filter(
    SpiderAudit.spider_name == "eastmoney_stock_quote"
).limit(10).all()

# 统计
count = await SpiderAudit.filter(
    SpiderAudit.status == "success"
).count()
```

---

## 审计 API

### 统计数据

```bash
GET /api/v1/spider-audit/stats
```

```json
{
  "total_runs": 1234,
  "success_rate": 0.95,
  "avg_execution_time": 1.23,
  "top_spiders": [
    {"spider_name": "eastmoney_stock_quote", "count": 456}
  ]
}
```

### 查询记录

```bash
GET /api/v1/spider-audit/records?spider_name=eastmoney_stock_quote&limit=10
```

### 清理旧数据

```bash
DELETE /api/v1/spider-audit/cleanup?days=30
```

---

## 数据备份

### 备份脚本

```bash
# 备份数据库
cp omnidata.db omnidata.db.backup.$(date +%Y%m%d)

# 或使用 SQLite 导出
sqlite3 omnidata.db .dump > backup.sql
```

### 恢复数据

```bash
# 从备份恢复
cp omnidata.db.backup.20260211 omnidata.db

# 或从 SQL 恢复
sqlite3 omnidata.db < backup.sql
```

---

## 性能优化

### 索引策略

- `spider_name`：高频查询字段
- `created_at`：时间范围查询
- `status`：状态过滤

### 清理策略

```python
# 定期清理旧数据
async def cleanup_old_audits(days: int = 90):
    cutoff = datetime.now() - timedelta(days=days)
    await SpiderAudit.filter(
        SpiderAudit.created_at < cutoff
    ).delete()
```

---

## 配置

通过环境变量配置：

```bash
# 数据库路径
OMNIDATA_DB__PATH=omnidata.db

# 审计日志保留天数
OMNIDATA_AUDIT__RETENTION_DAYS=90
```

---

详见：
- [系统架构概览](overview.md)
- [监控 API](../api/monitoring.md)
