# 获取个股、指数、ETF基金的实时资金流向数据，包括主力、超大单、大单、中单、小单的净流入及占比，以及5日、10日累计资金流向

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_realtime_stock_fund_flow` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `secid` | `str` | ✓ | - | 证券ID，格式：市场ID.代码，例如：1.000001(上证指数)、0.000001(平安银行)、1.516920（芯片ETF）。市场ID：0=深圳，1=上海 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_realtime_stock_fund_flow",
    "params": { ... }
  }'
```

### Python SDK

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/api/v1/spiders/run",
        json={
            "spider_name": "eastmoney_realtime_stock_fund_flow",
            "params": { ... }
        }
    )
    result = resp.json()
```

## 返回格式

```json
{
  "success": true,
  "message": "执行成功",
  "data": { ... },
  "execution_time": 1.23
}
```
