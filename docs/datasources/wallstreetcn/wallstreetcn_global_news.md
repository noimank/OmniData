# 获取华尔街见闻7x24小时快讯新闻列表，支持多频道筛选（要闻/A股/美股/港股/外汇/商品/债券/科技），包括标题、内容、发布时间、链接等

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `wallstreetcn_global_news` |
| **平台** | 华尔街见闻 |
| **版本** | 1.1.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `channel` | `Literal['global', 'a-stock', 'us-stock', 'hk-stock', 'forex', 'commodity', 'bond', 'tech']` | ✗ | `global` | 新闻频道：global-要闻，a-stock-A股，us-stock-美股，hk-stock-港股，forex-外汇，commodity-商品，bond-债券，tech-科技 |
| `limit` | `int` | ✗ | `20` | 每次获取新闻数量，默认20条，最大100条 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "wallstreetcn_global_news",
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
            "spider_name": "wallstreetcn_global_news",
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
