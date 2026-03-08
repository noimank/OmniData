# Eastmoney Industry Sector Flow

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_industry_sector_flow`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取行业板块最新资金流向排行数据

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `limit` | string | ✗ | 获取数据条数，最多128条, 默认: `128` |
| `rank_type` | string | ✗ | 排行类型：today=今日排行, 5day=5日排行, 10day=10日排行, 默认: `today` |
| `data_format` | string | ✗ | 返回格式：json, dict, markdown, string, 默认: `json` |

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
    "spider_name": "eastmoney_industry_sector_flow",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_industry_sector_flow",
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
