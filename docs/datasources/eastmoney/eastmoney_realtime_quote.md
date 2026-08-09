# 批量获取多只股票/指数/ETF实时行情报价，包括最新价、涨跌幅、成交量、成交额、振幅、换手率、量比、市盈率、市净率、总市值等完整行情数据，支持自动分批

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_realtime_quote` |
| **平台** | 东方财富 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `secids` | `str` | ✓ | - | 证券标识，逗号分隔，每项支持两种格式：① 完整 secid（market.code），如 '1.600519'(贵州茅台)、'1.000001'(上证指数)、'0.920002'(北交所)；② 裸 6 位代码自动推断市场，如 '600519'、'000001'、'300750'、'510050'。注意：'000001' 等代码存在歧义（平安银行 vs 上证指数），自动推断按股票处理，指数请显式传 '1.000001' |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_realtime_quote",
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
            "spider_name": "eastmoney_realtime_quote",
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
