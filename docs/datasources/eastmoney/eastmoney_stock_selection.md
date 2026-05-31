# 东方财富条件选股，通过自然语言查询获取符合条件的股票列表

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_stock_selection` |
| **平台** | 东方财富 |
| **版本** | 2.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `query_text` | `str` | ✓ | - | 选股条件文本，例如：换手率介于5%~10%;涨跌幅大于3% |
| `page_num` | `int` | ✗ | `1` | 页码，从1开始 |
| `page_size` | `int` | ✗ | `50` | 每页数量，默认50，最大500 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_stock_selection",
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
            "spider_name": "eastmoney_stock_selection",
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
