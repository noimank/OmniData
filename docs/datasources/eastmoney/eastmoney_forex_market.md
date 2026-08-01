# 获取外汇市场各货币对实时行情数据，支持分页、排序和市场筛选

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_forex_market` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page` | `int` | ✗ | `1` | 页码，从1开始 |
| `page_size` | `int` | ✗ | `20` | 每页数量，最大100 |
| `sort_field` | `Literal['f2', 'f3', 'f4', 'f12']` | ✗ | `f3` | 排序字段，f3=涨跌幅, f2=最新价, f4=涨跌额, f12=货币对代码 |
| `sort_order` | `Literal['desc', 'asc']` | ✗ | `desc` | 排序方向，desc=降序, asc=升序 |
| `market` | `Literal['all', '119', '120', '133']` | ✗ | `all` | 外汇市场筛选：all=全部外汇行情, 119=外汇行情(主要货币对), 120=外汇行情(中间价), 133=外汇行情(交叉盘) |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_forex_market",
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
            "spider_name": "eastmoney_forex_market",
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
