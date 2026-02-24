# Eastmoney Stock Billboard

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_stock_billboard`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取A股个股历史龙虎榜上榜数据，包括上榜原因、涨跌幅、买卖金额、营业部净买入以及上榜后多日涨跌幅等完整数据，支持日期范围查询

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `stock_code` | string | ✓ | 股票代码，6位数字，例如：000001(平安银行)、600000(浦发银行) |
| `start_date` | string | ✗ | 开始日期，格式：yyyyMMdd，例如：20200101，默认20200101, 默认: `20200101` |
| `end_date` | string | ✗ | 结束日期，格式：yyyyMMdd，例如：20251231，默认20500101, 默认: `20500101` |
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
    "spider_name": "eastmoney_stock_billboard",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_stock_billboard",
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
