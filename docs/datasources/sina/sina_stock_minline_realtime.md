# 获取个股/ETF当日实时分时数据（分钟级开盘/最高/最低/收盘/成交量/成交额），盘中即可获取，

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `sina_stock_minline_realtime` |
| **平台** | 新浪财经 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `symbol` | `str` | ✓ | - | 证券标识，支持两种格式：① 新浪前缀格式，如 'sh600519'(贵州茅台)、'sz000001'(平安银行)；② 裸 6 位代码自动推断市场：92/8/4 开头→北交所，6/5/9 开头→沪市，其余→深市 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |
| `limit` | `int | None` | ✗ | - | 返回分时条数上限，取当日最近 N 条；默认不填返回全部 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "sina_stock_minline_realtime",
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
            "spider_name": "sina_stock_minline_realtime",
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
