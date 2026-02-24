# Eastmoney Stock Quote

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_stock_quote`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.2.0

## 功能说明

获取A股/ETF基金实时行情报价数据，包括最新价、涨跌幅、成交量、成交额、买卖五价、市值、市盈率等完整行情数据

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `stock_code` | string | ✓ | 股票代码，6位数字，例如：000001(平安银行)、000002(万科A)、600000(浦发银行) |

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
    "spider_name": "eastmoney_stock_quote",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_stock_quote",
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
