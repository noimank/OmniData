# 获取A股/ETF基金历史日线K线数据，包括开高低收、成交量成交额、涨跌幅等完整K线数据，支持前复权/后复权/不复权，支持日期范围查询

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_stock_daily_kline` |
| **平台** | 东方财富 |
| **版本** | 1.1.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `stock_code` | `str` | ✓ | - | 股票代码，6位数字，例如：000001(平安银行)、600000(浦发银行)、516920（芯片ETF） |
| `start_date` | `str` | ✗ | `19900101` | 开始日期，格式：yyyyMMdd，例如：20200101，默认19900101 |
| `end_date` | `str` | ✗ | `20500101` | 结束日期，格式：yyyyMMdd，例如：20251231，默认20500101 |
| `adjust_type` | `Literal['qfq', 'hfq', 'none']` | ✗ | `qfq` | 复权类型，可选值：qfq(前复权)、hfq(后复权)、none(不复权)，默认前复权 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_stock_daily_kline",
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
            "spider_name": "eastmoney_stock_daily_kline",
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
