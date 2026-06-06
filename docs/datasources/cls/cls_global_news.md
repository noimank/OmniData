# 获取财联社全球财经快讯，支持筛选重点新闻（全部/重点）

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `cls_global_news` |
| **平台** | 财联社 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `symbol` | `str` | ✗ | `全部` | 筛选类型。全部=获取全部新闻，重点=仅获取A级和B级重点新闻 |
| `rn` | `int` | ✗ | `50` | 每页新闻数量，默认50条 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "cls_global_news",
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
            "spider_name": "cls_global_news",
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
