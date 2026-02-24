# Eastmoney Fast News

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_fast_news`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取东方财富全球财经快讯新闻列表，包括标题、摘要、时间、评论数、分享数等

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `page_size` | string | ✗ | 每页新闻数量，默认50条，最大100条, 默认: `50` |
| `fast_column` | string | ✗ | 快讯栏目代码，多个用逗号分割，如 '102,110,111'。101=焦点, 102=全球财经, 103=上市公司, 110=必读, 111=港股, 112=外汇, 113=期货, 114=期权, 115=债券, 116=基金, 117=数据, 默认: `102` |

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
    "spider_name": "eastmoney_fast_news",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_fast_news",
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
