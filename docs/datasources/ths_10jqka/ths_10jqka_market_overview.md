# 获取同花顺A股市场涨跌分布概览数据（10区间分布、涨跌停、大盘评级）

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `ths_10jqka_market_overview` |
| **平台** | 同花顺10jqka |
| **版本** | 3.0.0 |
| **作者** | noimank |

## 请求参数

该接口无需参数。

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "ths_10jqka_market_overview"
  }'
```

### Python SDK

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/api/v1/spiders/run",
        json={
            "spider_name": "ths_10jqka_market_overview"
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
