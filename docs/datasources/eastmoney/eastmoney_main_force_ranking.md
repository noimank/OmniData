# 获取沪深两市主力资金净流入排行数据，支持分页、排序（主力净占比/主力净流入/涨跌幅等）和市场筛选

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_main_force_ranking` |
| **平台** | 东方财富 |
| **版本** | 2.1.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page` | `int` | ✗ | `1` | 页码，从1开始 |
| `page_size` | `int` | ✗ | `50` | 每页数量，最大100 |
| `sort_field` | `Literal['f184', 'f62', 'f3', 'f109']` | ✗ | `f184` | 排序字段，f184=主力净占比, f62=主力净流入(元), f3=涨跌幅, f109=主力净流入占比 |
| `sort_order` | `Literal['desc', 'asc']` | ✗ | `desc` | 排序方向，desc=降序, asc=升序 |
| `market` | `Literal['all', 'sh', 'sz', 'kcb', 'cyb', 'sh_b', 'sz_b']` | ✗ | `all` | 市场范围：all=沪深A股, sh=沪市A股, sz=深市A股, kcb=科创板, cyb=创业板, sh_b=沪市B股, sz_b=深市B股 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_main_force_ranking",
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
            "spider_name": "eastmoney_main_force_ranking",
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
