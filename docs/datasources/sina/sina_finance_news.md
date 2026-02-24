# Sina Finance News

!!! abstract "接口信息"
    - **爬虫名称**：`sina_finance_news`
    - **平台**：新浪财经
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取新浪财经7x24小时全球财经快讯，支持按标签筛选（全部/宏观/公司/数据/市场/观点/央行/其他/A股/国际）

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `page` | string | ✗ | 页码，默认第1页, 默认: `1` |
| `page_size` | string | ✗ | 每页新闻数量，默认20条，最大100条, 默认: `20` |
| `tag_id` | string | ✗ | 标签ID，筛选新闻分类。0=全部, 1=宏观, 3=公司, 4=数据, 5=市场, 6=观点, 7=央行, 8=其他, 10=A股, 102=国际, 默认: `0` |

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
    "spider_name": "sina_finance_news",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "sina_finance_news",
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
