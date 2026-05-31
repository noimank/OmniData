# 获取指定日期范围的龙虎榜交易明细数据，包括上榜股票、涨跌幅、龙虎榜买卖金额等

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_daily_billboard_details` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `start_date` | `str` | ✗ | `` | 开始日期，格式：YYYY-MM-DD，如 2026-01-14，默认为当天 |
| `end_date` | `str` | ✗ | `` | 结束日期，格式：YYYY-MM-DD，如 2026-01-16，默认为当天 |
| `limit` | `int` | ✗ | `100` | 获取数据条数，最多1000条 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_daily_billboard_details",
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
            "spider_name": "eastmoney_daily_billboard_details",
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
