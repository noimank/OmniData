# Eastmoney Stock Daily Kline

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_stock_daily_kline`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.1.0

## 功能说明

获取A股/ETF基金历史日线K线数据，包括开高低收、成交量成交额、涨跌幅等完整K线数据，支持前复权/后复权/不复权，支持日期范围查询

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `stock_code` | string | ✓ | 股票代码，6位数字，例如：000001(平安银行)、600000(浦发银行)、516920（芯片ETF） |
| `start_date` | string | ✗ | 开始日期，格式：yyyyMMdd，例如：20200101，默认19900101, 默认: `19900101` |
| `end_date` | string | ✗ | 结束日期，格式：yyyyMMdd，例如：20251231，默认20500101, 默认: `20500101` |
| `adjust_type` | string | ✗ | 复权类型，可选值：qfq(前复权)、hfq(后复权)、none(不复权)，默认前复权, 默认: `qfq` |
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
    "spider_name": "eastmoney_stock_daily_kline",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_stock_daily_kline",
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
