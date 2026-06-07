# 获取ETF/LOF基金历史净值数据，包括单位净值、累计净值、日增长率、申赎状态、分红送配等信息，支持日期范围筛选

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_fund_nav_history` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `fund_code` | `str` | ✓ | - | 基金代码，6位数字，例如：159559（机器人ETF景顺）、510050（上证50ETF）、510300（沪深300ETF） |
| `start_date` | `str | None` | ✗ | - | 开始日期，格式：yyyyMMdd，例如：20260101，不填则从成立日开始 |
| `end_date` | `str | None` | ✗ | - | 结束日期，格式：yyyyMMdd，例如：20260607，不填则到最新净值日 |
| `data_format` | `Literal['json', 'dict', 'csv', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, csv, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_fund_nav_history",
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
            "spider_name": "eastmoney_fund_nav_history",
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
