# 获取A股个股历史龙虎榜上榜数据，包括上榜原因、涨跌幅、买卖金额、营业部净买入以及上榜后多日涨跌幅等完整数据，支持日期范围查询

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_stock_billboard` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `stock_code` | `str` | ✓ | - | 股票代码，6位数字，例如：000001(平安银行)、600000(浦发银行) |
| `start_date` | `str` | ✗ | `20200101` | 开始日期，格式：yyyyMMdd，例如：20200101，默认20200101 |
| `end_date` | `str` | ✗ | `20500101` | 结束日期，格式：yyyyMMdd，例如：20251231，默认20500101 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_stock_billboard",
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
            "spider_name": "eastmoney_stock_billboard",
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
