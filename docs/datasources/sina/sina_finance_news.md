# 获取新浪财经7x24小时全球财经快讯，支持按标签筛选（全部/宏观/公司/数据/市场/观点/央行/其他/A股/国际）

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `sina_finance_news` |
| **平台** | 新浪财经 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page` | `int` | ✗ | `1` | 页码，默认第1页 |
| `page_size` | `int` | ✗ | `20` | 每页新闻数量，默认20条，最大100条 |
| `tag_id` | `int` | ✗ | `0` | 标签ID，筛选新闻分类。0=全部, 1=宏观, 3=公司, 4=数据, 5=市场, 6=观点, 7=央行, 8=其他, 10=A股, 102=国际 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "sina_finance_news",
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
            "spider_name": "sina_finance_news",
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
