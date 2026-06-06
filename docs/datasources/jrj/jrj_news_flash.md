# 获取金融界24小时快讯新闻列表，包括标题、内容、发布时间、来源、链接等

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `jrj_news_flash` |
| **平台** | 金融界 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

该接口无需参数。

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "jrj_news_flash"
  }'
```

### Python SDK

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/api/v1/spiders/run",
        json={
            "spider_name": "jrj_news_flash"
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
