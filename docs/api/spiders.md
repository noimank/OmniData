# 爬虫 API

OmniData RESTful API 参考。

---

## 基础信息

- **Base URL**：`http://localhost:8380`
- **Content-Type**：`application/json`

---

## 爬虫管理

### 列出所有爬虫

```http
GET /spiders
```

**响应示例**：

```json
{
  "spiders": [
    {
      "name": "eastmoney_stock_quote",
      "description": "获取股票实时行情",
      "platform": "东方财富",
      "version": "1.0.0",
      "author": "noimank",
      "enabled": true,
      "params_schema": {
        "secucode": {"type": "string", "description": "股票代码"}
      }
    }
  ]
}
```

### 获取爬虫详情

```http
GET /spiders/{spider_name}
```

### 运行爬虫

```http
POST /spiders/run
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

**响应示例**：

```json
{
  "success": true,
  "data": {
    "name": "平安银行",
    "price": 12.50
  },
  "metadata": {
    "execution_time": 1.23,
    "spider_name": "eastmoney_stock_quote"
  }
}
```

### 批量运行爬虫

```http
POST /spiders/run-batch
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

---

## 错误响应

### 参数验证错误

```json
{
  "detail": [
    {
      "loc": ["body", "params", "secucode"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 爬虫执行失败

```json
{
  "success": false,
  "error": "网络请求超时",
  "metadata": {
    "spider_name": "eastmoney_stock_quote",
    "execution_time": 30.0
  }
}
```

---

## 完整示例

### Python

```python
import httpx

async def get_stock_quote(secucode: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8380/spiders/run",
            json={
                "spider_name": "eastmoney_stock_quote",
                "params": {"secucode": secucode}
            }
        )
        return resp.json()

result = await get_stock_quote("000001")
print(result["data"]["price"])
```

### JavaScript

```javascript
async function getStockQuote(secucode) {
  const resp = await fetch('http://localhost:8380/spiders/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      spider_name: 'eastmoney_stock_quote',
      params: {secucode}
    })
  });
  return await resp.json();
}

const result = await getStockQuote('000001');
console.log(result.data.price);
```

### cURL

```bash
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "eastmoney_stock_quote",
    "params": {"secucode": "000001"}
  }'
```

---

## 更多 API

- [MCP API](mcp.md) - MCP 服务管理
- [监控 API](monitoring.md) - 浏览器池监控
