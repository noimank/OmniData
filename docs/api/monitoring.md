# 监控 API

系统监控和统计 API 参考。

---

## 浏览器池监控

### 获取浏览器池状态

```http
GET /api/v1/monitor/browser-pool
```

**响应示例**（统一 `ApiResponse` 包装）：

```json
{
  "success": true,
  "message": "获取浏览器池状态成功",
  "data": {
    "browser_count": 1,
    "context_count": 5,
    "active_pages": 2,
    "total_contexts_created": 120,
    "total_contexts_reused": 480,
    "reuse_rate": 0.8,
    "total_contexts_closed": 100,
    "total_browser_recycles": 3,
    "total_browser_recoveries": 1,
    "pages_since_recycle": 1234,
    "last_recycle_at": 1752552000.0,
    "config": {
      "idle_timeout": 600,
      "headless": true,
      "user_agent": "Mozilla/5.0 ... Chrome/143.0.0.0 Safari/537.36"
    }
  }
}
```

### 获取当前 Context 列表

```http
GET /api/v1/monitor/contexts
```

```json
{
  "success": true,
  "message": "获取 Context 列表成功",
  "data": [
    {
      "namespace": "eastmoney",
      "key": "eastmoney",
      "created_at": 1752552000.0,
      "last_used_at": 1752555600.0,
      "idle_time": 12.3,
      "pages_count": 0
    }
  ]
}
```

### 获取系统资源

```http
GET /api/v1/monitor/system
```

```json
{
  "success": true,
  "message": "获取系统状态成功",
  "data": {
    "status": "healthy",
    "uptime_seconds": 86400.0,
    "memory_usage_mb": 356.2,
    "memory_percent": 4.5,
    "cpu_percent": 2.3,
    "redis_connected": true,
    "timestamp": "2026-08-14T10:00:00"
  }
}
```

---

## 健康检查

### 服务健康状态

```http
GET /health
```

**响应示例**：

```json
{
  "success": true,
  "message": "服务正常",
  "data": {
    "status": "healthy",
    "service": "omnidata"
  }
}
```

---

## 审计日志

### 获取统计数据

```http
GET /api/v1/spider-audit/stats
```

### 查询记录

```http
GET /api/v1/spider-audit/records?spider_name=eastmoney_stock_quote&limit=10&offset=0
```

### 查询平台列表

```http
GET /api/v1/spider-audit/platforms
```

### 查询爬虫列表

```http
GET /api/v1/spider-audit/spiders
```

### 清理旧数据

```http
DELETE /api/v1/spider-audit/cleanup?days=30
```

### 批量删除记录

```http
DELETE /api/v1/spider-audit/records/batch
```

### 删除单条记录

```http
DELETE /api/v1/spider-audit/records/{record_id}
```

---

## 更多 API

- [爬虫 API](spiders.md) - 爬虫管理
- [MCP API](mcp.md) - MCP 服务管理
