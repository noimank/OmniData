# 获取东方财富全球财经快讯新闻列表，包括标题、摘要、时间、评论数、分享数等

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `eastmoney_fast_news` |
| **平台** | 东方财富 |
| **版本** | 1.2.1 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page_size` | `int` | ✗ | `50` | 每页新闻数量，默认50条，最大100条 |
| `fast_column` | `str` | ✗ | `102` | 快讯栏目代码，多个用逗号分割，如 '102,110,111'。101=焦点, 102=全球财经, 103=上市公司, 110=必读, 111=港股, 112=外汇, 113=期货, 114=期权, 115=债券, 116=基金, 117=数据 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "eastmoney_fast_news",
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
            "spider_name": "eastmoney_fast_news",
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
