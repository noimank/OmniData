# 获取指定行业板块的历史资金流向数据（日线/周线/月线）

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_industry_history_flow` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `sector_code` | `str` | ✓ | - | 行业板块代码，如：BK0737（软件开发）、BK0420（航空机场） |
| `period` | `Literal['day', 'week', 'month']` | ✗ | `day` | K线周期：day=日线, week=周线, month=月线 |
| `limit` | `int` | ✗ | `0` | 限制返回数据条数，0表示全部数据 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回格式：json, dict, markdown, string |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_industry_history_flow",
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
            "spider_name": "eastmoney_industry_history_flow",
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
