# Eastmoney China Cpi

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_china_cpi`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取中国CPI居民消费价格指数月度数据，包括全国、城市、农村的当月同比、环比增长及累计数据

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `limit` | string | ✗ | 每页数量，默认200条，最大500条, 默认: `50` |

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
    "spider_name": "eastmoney_china_cpi",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_china_cpi",
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
