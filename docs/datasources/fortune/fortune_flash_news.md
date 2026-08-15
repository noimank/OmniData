# 获取 Fortune 最新新闻快讯，包括标题、摘要、发布时间、链接等

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `fortune_flash_news` |
| **平台** | 财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `num` | `int` | ✗ | `30` | 获取快讯数量，默认30条，最大100条（WordPress 接口单页上限） |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "fortune_flash_news",
    "params": { ... }
  }'
```

### Python SDK

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/api/v1/spiders/run",
        json={
            "spider_name": "fortune_flash_news",
            "params": { ... }
        }
    )
    result = resp.json()
```

## 返回格式

```json
{
  "success": true,
  "message": "执行成功",
  "data": { ... },
  "execution_time": 1.23
}
```
