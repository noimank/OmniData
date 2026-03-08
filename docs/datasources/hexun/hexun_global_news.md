# 获取和讯网7x24小时快讯新闻列表，包括标题、摘要、发布时间、来源、链接等

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `hexun_global_news` |
| **平台** | 和讯网 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page` | `int` | ✗ | `1` | 页码，默认第1页 |
| `page_size` | `int` | ✗ | `20` | 每页新闻数量，默认20条，最大100条 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "hexun_global_news",
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
            "spider_name": "hexun_global_news",
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
