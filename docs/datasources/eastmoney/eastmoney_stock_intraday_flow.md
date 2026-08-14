# 获取个股/ETF分时资金流向数据（分钟级别），包括主力、超大单、大单、中单、小单的净流入

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_stock_intraday_flow` |
| **平台** | 东方财富 |
| **版本** | 2.1.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `stock_code` | `str` | ✓ | - | 股票或ETF代码，如 000001（平安银行）、516920（芯片ETF） |
| `limit` | `int` | ✗ | `0` | 获取最近多少条分时数据，0表示全部 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_stock_intraday_flow",
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
            "spider_name": "eastmoney_stock_intraday_flow",
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
