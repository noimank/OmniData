# MCP API

MCP 服务管理 API 参考。

---

## MCP 服务管理

### 列出所有服务

```http
GET /api/v1/mcp-services
```

**响应示例**：

```json
{
  "services": [
    {
      "id": 1,
      "name": "financial-data",
      "description": "金融数据查询服务",
      "spider_names": ["eastmoney_stock_quote", "sina_global_news"],
      "transport": "streamable-http",
      "enabled": true,
      "created_at": "2026-02-11T10:00:00"
    }
  ]
}
```

### 创建 MCP 服务

```http
POST /api/v1/mcp-services
```

**请求体**：

```json
{
  "name": "financial-data",
  "description": "金融数据查询服务",
  "spider_names": ["eastmoney_stock_quote", "eastmoney_market_flow"],
  "transport": "streamable-http"
}
```

### 获取服务详情

```http
GET /api/v1/mcp-services/{id}
```

### 获取服务工具提示

```http
GET /api/v1/mcp-services/{id}/prompts
```

### 更新工具提示

```http
PUT /api/v1/mcp-services/{id}/tools/{tool_id}/prompt
```

**请求体**：

```json
{
  "user_prompt": "你是股票查询助手...",
  "version": "1.0"
}
```

### 删除服务

```http
DELETE /api/v1/mcp-services/{id}
```

---

## MCP 端点

### 服务端点

创建服务后，可通过以下端点访问：

```
http://localhost:8380/mcp/{service_name}
```

### Claude Desktop 配置

```json
{
  "mcpServers": {
    "omnidata": {
      "url": "http://localhost:8380/mcp/financial-data",
      "transport": "sse"
    }
  }
}
```

---

## 传输协议

| 协议 | 说明 |
| :--- | :--- |
| `http` | 标准 HTTP 请求/响应 |
| `streamable-http` | 支持流式响应 |
| `sse` | Server-Sent Events |

---

## 更多 API

- [爬虫 API](spiders.md) - 爬虫管理
- [监控 API](monitoring.md) - 浏览器池监控
