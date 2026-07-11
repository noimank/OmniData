# 获取全球主要指数涨跌幅排行数据，支持分页、排序和地区筛选（美股/港股/亚太/欧洲）

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_global_index_ranking` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page` | `int` | ✗ | `1` | 页码，从1开始 |
| `page_size` | `int` | ✗ | `50` | 每页数量，最大100 |
| `sort_field` | `Literal['f3', 'f2', 'f4', 'f7', 'f12']` | ✗ | `f3` | 排序字段，f3=涨跌幅, f2=最新点位, f4=涨跌点位, f7=振幅, f12=指数代码 |
| `sort_order` | `Literal['desc', 'asc']` | ✗ | `desc` | 排序方向，desc=降序, asc=升序 |
| `region` | `Literal['all', 'cn', 'us', 'hk', 'asia', 'europe', 'americas']` | ✗ | `all` | 市场筛选：all=全部, cn=沪深A股, us=美股, hk=港股, asia=亚太, europe=欧洲, americas=美洲其他 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_global_index_ranking",
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
            "spider_name": "eastmoney_global_index_ranking",
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
