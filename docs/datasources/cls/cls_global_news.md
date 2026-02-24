# Cls Global News

!!! abstract "接口信息"
    - **爬虫名称**：`cls_global_news`
    - **平台**：财联社
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取财联社全球财经快讯，支持筛选重点新闻（全部/重点）

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `symbol` | string | ✗ | 筛选类型。全部=获取全部新闻，重点=仅获取A级和B级重点新闻, 默认: `全部` |
| `rn` | string | ✗ | 每页新闻数量，默认50条, 默认: `50` |

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
    "spider_name": "cls_global_news",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "cls_global_news",
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
