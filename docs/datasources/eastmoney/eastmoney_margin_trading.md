# Eastmoney Margin Trading

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_margin_trading`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.1.0

## 功能说明

获取沪深北三市融资融券历史数据，支持查询全部/沪市/深市/京市，支持1日/3日/5日/10日统计周期

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `market` | string | ✗ | 市场类型，可选值：all(全部)、sh(沪市)、sz(深市)、bj(京市), 默认: `all` |
| `statistics` | string | ✗ | 统计周期，可选值：1d(1日数据)、3d(3日合计)、5d(5日合计)、10d(10日合计), 默认: `1d` |
| `limit` | string | ✗ | 获取最近多少个交易日的数据, 默认: `50` |
| `data_format` | string | ✗ | 返回数据格式，可选值：json, dict, string, markdown, 默认: `json` |

## 返回结果

```json
{
  "success": true,
  "data": { ... }
}
```

## 使用示例

```bash
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "eastmoney_margin_trading",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_margin_trading",
            "params": {{ ... }}
        }
    )
    result = resp.json()
```

## 注意事项

!!! tip "使用提示"
    具体使用方法请参考代码实现。

!!! warning "限制"
    请合理使用接口，避免频繁请求。
