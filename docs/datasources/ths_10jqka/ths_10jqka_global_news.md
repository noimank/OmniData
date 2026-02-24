# Ths 10Jqka Global News

!!! abstract "接口信息"
    - **爬虫名称**：`ths_10jqka_global_news`
    - **平台**：同花顺
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取同花顺全球财经快讯新闻列表，支持按标签筛选（全部/要闻/A股/港股/美股/基金/观点/公告）

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `page` | string | ✗ | 页码，默认第1页, 默认: `1` |
| `tag` | string | ✗ | 标签筛选，支持的数字ID: 21101=全部(默认), -21101=要闻, 21103=A股, 21105=港股, 21107=美股, 21109=基金, 21111=观点, 34843=公告, 默认: `21101` |

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
    "spider_name": "ths_10jqka_global_news",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "ths_10jqka_global_news",
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
