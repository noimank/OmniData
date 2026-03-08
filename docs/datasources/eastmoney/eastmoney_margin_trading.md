# 获取沪深北三市融资融券历史数据，支持查询全部/沪市/深市/京市，支持1日/3日/5日/10日统计周期

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_margin_trading` |
| **平台** | 东方财富 |
| **版本** | 1.1.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `market` | `Literal['all', 'sh', 'sz', 'bj']` | ✗ | `all` | 市场类型，可选值：all(全部)、sh(沪市)、sz(深市)、bj(京市) |
| `statistics` | `Literal['1d', '3d', '5d', '10d']` | ✗ | `1d` | 统计周期，可选值：1d(1日数据)、3d(3日合计)、5d(5日合计)、10d(10日合计) |
| `limit` | `int` | ✗ | `50` | 获取最近多少个交易日的数据 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_margin_trading",
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
            "spider_name": "eastmoney_margin_trading",
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
