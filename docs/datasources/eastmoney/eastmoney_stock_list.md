# Eastmoney Stock List

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_stock_list`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取沪深京A股实时行情列表数据，支持分页和排序

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `page` | string | ✗ | 页码，从1开始, 默认: `1` |
| `page_size` | string | ✗ | 每页数量，最大100, 默认: `20` |
| `sort_field` | string | ✗ | 排序字段，f3=涨跌幅, f2=最新价, f5=成交量, f6=成交额, f15=最高, f16=最低, 默认: `f3` |
| `sort_order` | string | ✗ | 排序方向，0=升序, 1=降序, 默认: `1` |

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
    "spider_name": "eastmoney_stock_list",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_stock_list",
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
