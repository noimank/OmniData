# 爬虫 API

OmniData RESTful API 参考。

---

## 基础信息

- **Base URL**：`http://localhost:8380`（Docker 部署时通过 nginx 对外暴露 80，即 `http://localhost/api/v1/...`）
- **Content-Type**：`application/json`
- **响应格式**：除爬虫执行结果外，统一使用 `ApiResponse<T>` 包装（`{success, message, data}`）

---

## 爬虫管理

### 列出所有爬虫

```http
GET /api/v1/spiders
```

**响应示例**：

```json
{
  "success": true,
  "message": "获取爬虫列表成功",
  "data": {
    "count": 3,
    "spiders": [
      {
        "name": "eastmoney_stock_quote",
        "description": "获取股票实时行情",
        "version": "1.0.0",
        "author": "noimank",
        "platform": "东方财富"
      }
    ]
  }
}
```

### 获取爬虫详情

```http
GET /api/v1/spiders/{spider_name}
```

### 获取爬虫参数 Schema

获取参数 JSON Schema，用于动态生成表单：

```http
GET /api/v1/spiders/{spider_name}/schema
```

```json
{
  "success": true,
  "message": "获取参数 schema 成功",
  "data": {
    "name": "eastmoney_stock_quote",
    "description": "获取股票实时行情",
    "version": "1.0.0",
    "params_schema": {
      "secucode": {
        "type": "string",
        "title": "secucode",
        "description": "股票代码",
        "default": null
      }
    },
    "required": ["secucode"]
  }
}
```

### 验证爬虫参数

```http
POST /api/v1/spiders/{spider_name}/validate
```

**请求体**：

```json
{
  "params": {"secucode": "000001"}
}
```

---

## 运行爬虫

### 运行爬虫

```http
POST /api/v1/spiders/run
```

**请求体**：

```json
{
  "spider_name": "eastmoney_stock_quote",
  "params": {
    "secucode": "000001"
  }
}
```

**响应示例**（直接返回 `SpiderResult`，不做 `ApiResponse` 包装）：

```json
{
  "spider_name": "eastmoney_stock_quote",
  "success": true,
  "data": {
    "name": "平安银行",
    "price": 12.5
  },
  "message": null,
  "started_at": "2026-08-14T10:00:00",
  "completed_at": "2026-08-14T10:00:01",
  "duration_seconds": 1.23,
  "metadata": {}
}
```

### 批量运行爬虫

```http
POST /api/v1/spiders/run-batch
```

**请求体**：

```json
{
  "spider_name": "eastmoney_stock_quote",
  "params_list": [
    {"secucode": "000001"},
    {"secucode": "000002"}
  ],
  "max_concurrency": 3
}
```

**响应示例**：

```json
{
  "count": 2,
  "results": [
    { "spider_name": "eastmoney_stock_quote", "success": true, "...": "SpiderResult" },
    { "spider_name": "eastmoney_stock_quote", "success": true, "...": "SpiderResult" }
  ]
}
```

---

## 错误响应

### 爬虫不存在

```json
{
  "success": false,
  "message": "爬虫不存在: xxx",
  "data": null
}
```

### 爬虫执行失败

```json
{
  "spider_name": "eastmoney_stock_quote",
  "success": false,
  "data": null,
  "message": "网络请求超时",
  "started_at": "2026-08-14T10:00:00",
  "completed_at": "2026-08-14T10:00:30",
  "duration_seconds": 30.0,
  "metadata": {}
}
```

---

## 完整示例

### cURL

```bash
# 运行爬虫
curl -X POST http://localhost:8380/api/v1/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "eastmoney_stock_quote",
    "params": {"secucode": "000001"}
  }'
```

### Python

```python
import httpx

async def get_stock_quote(secucode: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8380/api/v1/spiders/run",
            json={
                "spider_name": "eastmoney_stock_quote",
                "params": {"secucode": secucode}
            }
        )
        return resp.json()

result = await get_stock_quote("000001")
print(result["data"]["price"])
```

---

## 更多 API

- [MCP API](mcp.md) - MCP 服务管理
- [监控 API](monitoring.md) - 浏览器池监控
