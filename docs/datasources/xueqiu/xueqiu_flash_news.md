# 获取雪球7x24实时财经快讯，包括内容、时间、链接等

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `xueqiu_flash_news` |
| **平台** | 雪球 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `limit` | `int` | ✗ | `10` | 获取快讯数量，默认10条，最大50条（API单次最多返回10条，超出会自动分页） |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "xueqiu_flash_news",
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
            "spider_name": "xueqiu_flash_news",
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
