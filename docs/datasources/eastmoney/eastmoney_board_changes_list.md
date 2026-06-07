# 获取全市场板块的当日盘口异动详情，包括每个板块的异动总次数、涨跌幅、主力资金流、最大异动股以及各类型异动次数明细（28 种）

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_board_changes_list` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page` | `int` | ✗ | `1` | 页码，从 1 开始 |
| `page_size` | `int` | ✗ | `100` | 每页板块数量，最大 2000（一次可拉全市场） |
| `sort_field` | `Literal['ct', 'u', 'zjl']` | ✗ | `ct` | 排序字段：ct=异动总次数, u=涨跌幅(%), zjl=主力资金流(元) |
| `sort_dir` | `Literal['desc', 'asc']` | ✗ | `desc` | 排序方向：desc=降序, asc=升序 |
| `min_change_count` | `int` | ✗ | `0` | 过滤：仅保留异动总次数 >= 该值的板块，0 不过滤 |
| `change_type` | `int | None` | ✗ | - | 过滤：仅保留包含指定异动类型（编号）的板块，None 不过滤。 可选：1/2/4/8/16/32/64/128/256/512/8193/8194/8201-8222 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_board_changes_list",
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
            "spider_name": "eastmoney_board_changes_list",
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
