# 获取A股/ETF筹码分布数据，包括获利比例、平均成本、90%/70%筹码集中度等指标，用于分析筹码结构和成本分布

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_stock_chip_distribution` |
| **平台** | 东方财富 |
| **版本** | 2.1.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `stock_code` | `str` | ✓ | - | 股票代码，6位数字，例如：000001(平安银行)、159382(创业板人工智能ETF南方), |
| `adjust_type` | `Literal['qfq', 'hfq', 'none']` | ✗ | `qfq` | 复权类型，可选值：qfq(前复权)、hfq(后复权)、none(不复权)，默认前复权 |
| `kline_limit` | `int` | ✗ | `500` | 计算筹码分布的历史K线数量，影响计算精度：默认500条(约2年)，建议不少于100条；更多K线=更长期筹码历史=更高精度，但计算更慢 |
| `days` | `int` | ✗ | `90` | 返回最近N天的筹码分布数据，默认90天，范围1-500 |
| `data_format` | `Literal['json', 'dict', 'markdown', 'string']` | ✗ | `json` | 返回数据格式，可选值：json, dict, string, markdown |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_stock_chip_distribution",
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
            "spider_name": "eastmoney_stock_chip_distribution",
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
