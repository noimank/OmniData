# Eastmoney Active Department

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_active_department`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取指定日期范围的龙虎榜活跃营业部数据，包括营业部买卖金额、净买入额、上榜次数等

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `start_date` | string | ✗ | 开始日期，格式：YYYY-MM-DD，如 2026-01-14，默认为当天, 默认: `` |
| `end_date` | string | ✗ | 结束日期，格式：YYYY-MM-DD，如 2026-01-16，默认为当天, 默认: `` |
| `limit` | string | ✗ | 获取数据条数，最多1000条, 默认: `60` |
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
    "spider_name": "eastmoney_active_department",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_active_department",
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
