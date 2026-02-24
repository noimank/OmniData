# Eastmoney Stock Chip Distribution

!!! abstract "接口信息"
    - **爬虫名称**：`eastmoney_stock_chip_distribution`
    - **平台**：东方财富
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取A股/ETF筹码分布数据，包括获利比例、平均成本、90%/70%筹码集中度等指标，用于分析筹码结构和成本分布

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `stock_code` | string | ✓ | 股票代码，6位数字，例如：000001(平安银行)、159382(创业板人工智能ETF南方), |
| `adjust_type` | string | ✗ | 复权类型，可选值：qfq(前复权)、hfq(后复权)、none(不复权)，默认前复权, 默认: `qfq` |
| `kline_limit` | string | ✗ | 计算筹码分布的历史K线数量，影响计算精度：默认500条(约2年)，建议不少于100条；更多K线=更长期筹码历史=更高精度，但计算更慢, 默认: `500` |
| `days` | string | ✗ | 返回最近N天的筹码分布数据，默认90天，范围1-500, 默认: `90` |
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
    "spider_name": "eastmoney_stock_chip_distribution",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "eastmoney_stock_chip_distribution",
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
