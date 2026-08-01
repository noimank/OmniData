# 获取沪深两市ETF基金最新涨跌排行数据，支持分页和排序

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_etf_ranking` |
| **平台** | 东方财富 |
| **版本** | 2.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page` | `int` | ✗ | `1` | 页码，从1开始 |
| `page_size` | `int` | ✗ | `20` | 每页数量，最大100 |
| `sort_field` | `Literal['f2', 'f3', 'f5', 'f6', 'f15', 'f16']` | ✗ | `f3` | 排序字段，f3=涨跌幅, f2=最新价, f5=成交量, f6=成交额, f15=最高, f16=最低 |
| `sort_order` | `Literal['desc', 'asc']` | ✗ | `desc` | 排序方向，desc=降序, asc=升序 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_etf_ranking",
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
            "spider_name": "eastmoney_etf_ranking",
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
