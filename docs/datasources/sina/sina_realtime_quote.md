# 批量获取多只股票/指数/ETF实时行情报价，包括最新价、涨跌额、涨跌幅、成交量、成交额、振幅、买卖五档盘口等，免登录免Key，浏览器请求自动分批

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `sina_realtime_quote` |
| **平台** | 新浪财经 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `symbols` | `str` | ✓ | - | 证券标识，逗号分隔，每项支持两种格式：① 新浪前缀格式，如 'sh600519'(贵州茅台)、'sz000001'(平安银行)、'bj920000'(北交所)；② 裸 6 位代码自动推断市场：92/8/4 开头→北交所，6/5/9 开头→沪市，其余→深市。注意：'000001' 存在歧义（平安银行 vs 上证指数），裸代码按股票处理，指数请显式传 'sh000001' |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "sina_realtime_quote",
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
            "spider_name": "sina_realtime_quote",
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
