# Wallstreetcn Global News

!!! abstract "接口信息"
    - **爬虫名称**：`wallstreetcn_global_news`
    - **平台**：华尔街见闻
    - **作者**：noimank
    - **版本**：1.1.0

## 功能说明

获取华尔街见闻7x24小时快讯新闻列表，支持多频道筛选（要闻/A股/美股/港股/外汇/商品/债券/科技），包括标题、内容、发布时间、链接等

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `channel` | string | ✗ | 新闻频道：global-要闻，a-stock-A股，us-stock-美股，hk-stock-港股，forex-外汇，commodity-商品，bond-债券，tech-科技, 默认: `global` |
| `limit` | string | ✗ | 每次获取新闻数量，默认20条，最大100条, 默认: `20` |

## 返回结果

```json
{
  "success": true,
  "data": { ... }
}
```

## 使用示例

```bash
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "wallstreetcn_global_news",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "wallstreetcn_global_news",
            "params": {{ ... }}
        }
    )
    result = resp.json()
```

## 注意事项

!!! tip "使用提示"
    具体使用方法请参考代码实现。

!!! warning "限制"
    请合理使用接口，避免频繁请求。
