# Eastmoney Stock Organization Trade

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_stock_organization_trade`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取单只股票的机构买卖统计数据，包括龙虎榜机构交易明细、买卖金额、上榜原因等

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `stock_code` | string | ✓ | 股票代码，如 601138、000001 |
| `limit` | string | ✗ | 获取最近多少条数据, 默认: `20` |
| `data_format` | string | ✗ | 返回数据格式，可选值：json, dict, string, markdown, 默认: `json` |

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
    "spider_name": "eastmoney_stock_organization_trade",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_stock_organization_trade",
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
