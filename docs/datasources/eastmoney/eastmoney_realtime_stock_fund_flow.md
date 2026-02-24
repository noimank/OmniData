# Eastmoney Realtime Stock Fund Flow

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_realtime_stock_fund_flow`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取个股、指数、ETF基金的实时资金流向数据，包括主力、超大单、大单、中单、小单的净流入及占比，以及5日、10日累计资金流向

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `secid` | string | ✓ | 证券ID，格式：市场ID.代码，例如：1.000001(上证指数)、0.000001(平安银行)、1.516920（芯片ETF）。市场ID：0=深圳，1=上海 |

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
    "spider_name": "eastmoney_realtime_stock_fund_flow",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_realtime_stock_fund_flow",
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
