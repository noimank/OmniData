# MCP API

MCP 服务管理 API 参考。

---

## MCP 服务管理

### 创建 MCP 服务

```http
POST /api/v1/mcp-services
```

**请求体**：

```json
{
  "name": "financial-data",
  "display_name": "金融数据服务",
  "description": "金融数据查询服务",
  "transport": "streamable-http",
  "tools": [
    {"spider_name": "eastmoney_stock_quote"},
    {"spider_name": "eastmoney_market_flow", "tool_name": "get_market_flow"}
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `name` | string | 是 | 服务名称（用于路由，唯一） |
| `display_name` | string | 是 | 显示名称 |
| `description` | string | 否 | 服务描述 |
| `transport` | string | 否 | `http` / `streamable-http` / `sse`，默认 `http` |
| `tools` | array | 是 | 工具列表（`spider_name` 必填，`tool_name` 可选，默认用爬虫名） |

创建成功后服务自动挂载到 `/mcp/{name}` 路径。

### 列出所有服务

```http
GET /api/v1/mcp-services
```

可选参数 `?is_active=true/false` 过滤状态。

```json
{
  "success": true,
  "message": "获取 MCP 服务列表成功",
  "data": [
    {
      "id": 1,
      "name": "financial-data",
      "display_name": "金融数据服务",
      "description": "金融数据查询服务",
      "transport": "streamable-http",
      "is_active": true,
      "created_at": "2026-08-14T10:00:00",
      "updated_at": "2026-08-14T10:00:00",
      "tool_count": 2
    }
  ]
}
```

### 获取服务详情

```http
GET /api/v1/mcp-services/{id}
```

### 更新服务

```http
PUT /api/v1/mcp-services/{id}
```

可更新 `display_name`、`description`、`transport`、`tools`（完整替换）。

### 激活 / 停用服务

```http
PUT /api/v1/mcp-services/{id}/activate
PUT /api/v1/mcp-services/{id}/deactivate
```

### 删除服务

```http
DELETE /api/v1/mcp-services/{id}
```

---

## 工具管理

### 列出服务工具

```http
GET /api/v1/mcp-services/{id}/tools
```

### 添加工具

```http
POST /api/v1/mcp-services/{id}/tools
```

**请求体**：

```json
{
  "spider_name": "sina_global_news",
  "tool_name": "get_global_news"
}
```

### 移除工具

```http
DELETE /api/v1/mcp-services/{id}/tools/{tool_id}
```

### 获取可用爬虫列表

```http
GET /api/v1/mcp-services/spiders/available
```

---

## 工具提示词版本

每个工具通过 `selected_prompt_version` 选择使用某个版本的爬虫提示词（`spider_prompt`），为空则使用该爬虫的默认版本。

### 获取工具当前提示词版本

```http
GET /api/v1/mcp-services/{id}/tools/{tool_id}/prompt-version
```

### 设置工具提示词版本

```http
PUT /api/v1/mcp-services/{id}/tools/{tool_id}/prompt-version
```

**请求体**：

```json
{
  "version_name": "详细版"
}
```

### 删除工具提示词版本

```http
DELETE /api/v1/mcp-services/{id}/tools/{tool_id}/prompt-version
```

---

## 爬虫提示词管理

提示词（`spider_prompt`）为全系统共享，按爬虫维度管理版本：

| 端点 | 说明 |
| :--- | :--- |
| `GET /api/v1/spider-prompts` | 列出提示词 |
| `POST /api/v1/spider-prompts` | 创建提示词版本 |
| `GET /api/v1/spider-prompts/{prompt_id}` | 获取提示词详情 |
| `PUT /api/v1/spider-prompts/{prompt_id}` | 更新提示词 |
| `DELETE /api/v1/spider-prompts/{prompt_id}` | 删除提示词 |
| `PUT /api/v1/spider-prompts/{prompt_id}/set-default` | 设为默认版本 |
| `GET /api/v1/spider-prompts/{prompt_id}/usage` | 查询使用情况 |
| `GET /api/v1/spider-prompts/spiders/{spider_name}/prompts` | 列出爬虫的提示词版本 |
| `POST /api/v1/spider-prompts/spiders/{spider_name}/prompts` | 为爬虫创建提示词版本 |
| `GET /api/v1/spider-prompts/spiders/{spider_name}/default-prompt` | 获取爬虫默认提示词 |
| `GET /api/v1/spider-prompts/spiders/available` | 获取可用爬虫列表 |

---

## MCP 端点

### 服务端点

创建服务后，通过以下端点访问：

```
http://localhost:8380/mcp/{service_name}
```

例如服务名 `financial-data`，访问路径为 `http://localhost:8380/mcp/financial-data`。

### Claude Desktop 配置

```json
{
  "mcpServers": {
    "omnidata": {
      "url": "http://localhost:8380/mcp/financial-data",
      "transport": "streamable-http"
    }
  }
}
```

---

## 传输协议

| 协议 | 说明 |
| :--- | :--- |
| `http` | 标准 HTTP 请求/响应 |
| `streamable-http` | 支持流式响应（推荐） |
| `sse` | Server-Sent Events |

---

## 更多 API

- [爬虫 API](spiders.md) - 爬虫管理
- [监控 API](monitoring.md) - 浏览器池监控
