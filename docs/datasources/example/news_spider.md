# News Spider

!!! abstract "接口信息"
    - **爬虫名称**：`news_spider`
    - **平台**：example
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

示例新闻爬虫，演示如何抓取列表数据

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `category` | string | ✗ | 新闻分类, 默认: `tech` |
| `limit` | string | ✗ | 获取数量限制, 默认: `10` |

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
    "spider_name": "news_spider",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "news_spider",
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
