# 获取ETF基金持仓明细数据，包括持仓股票、占净值比例、持股数、持仓市值等信息，支持按年份筛选

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_etf_holdings` |
| **平台** | 东方财富 |
| **版本** | 2.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `fund_code` | `str` | ✓ | - | 基金代码，6位数字，例如：159559（机器人ETF景顺）、510050（上证50ETF） |
| `year` | `str | None` | ✗ | - | 查询年份，例如：2026，不填则返回最新报告期数据 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_etf_holdings",
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
            "spider_name": "eastmoney_etf_holdings",
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
