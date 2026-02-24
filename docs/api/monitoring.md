# 监控 API

系统监控和统计 API 参考。

---

## 浏览器池监控

### 获取浏览器池状态

```http
GET /monitor/browser-pool
```

**响应示例**：

```json
{
  "total_contexts": 5,
  "active_contexts": 3,
  "idle_contexts": 2,
  "cache_stats": {
    "hits": 120,
    "misses": 15,
    "hit_rate": 0.889
  },
  "contexts": [
    {
      "namespace": "eastmoney_login",
      "created_at": "2026-02-11T10:00:00",
      "last_used_at": "2026-02-11T10:30:00",
      "page_count": 0,
      "status": "idle"
    }
  ]
}
```

---

## 审计日志

### 获取统计数据

```http
GET /api/v1/spider-audit/stats
```

**响应示例**：

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

```http
GET /api/v1/spider-audit/records?spider_name=eastmoney_stock_quote&limit=10&offset=0
```

**响应示例**：

```json
{
  "total": 456,
  "records": [
    {
      "id": 1,
      "spider_name": "eastmoney_stock_quote",
      "params": "{\"secucode\": \"000001\"}",
      "status": "success",
      "execution_time": 1.23,
      "created_at": "2026-02-11T10:00:00"
    }
  ]
}
```

### 清理旧数据

```http
DELETE /api/v1/spider-audit/cleanup?days=30
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
  "status": "healthy",
  "version": "0.1.0",
  "components": {
    "redis": "ok",
    "database": "ok",
    "browser_pool": "ok"
  }
}
```

---

## 更多 API

- [爬虫 API](spiders.md) - 爬虫管理
- [MCP API](mcp.md) - MCP 服务管理
