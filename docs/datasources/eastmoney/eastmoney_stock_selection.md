# Eastmoney Stock Selection

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_stock_selection`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：2.0.0

## 功能说明

东方财富条件选股，通过自然语言查询获取符合条件的股票列表

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `query_text` | string | ✓ | 选股条件文本，例如：换手率介于5%~10%;涨跌幅大于3% |
| `page_num` | string | ✗ | 页码，从1开始, 默认: `1` |
| `page_size` | string | ✗ | 每页数量，默认50，最大500, 默认: `50` |

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
    "spider_name": "eastmoney_stock_selection",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_stock_selection",
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
