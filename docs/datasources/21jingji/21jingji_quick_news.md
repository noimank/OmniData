# 21Jingji Quick News

!!! abstract "接口信息"
    - **爬虫名称**：`21jingji_quick_news`
    - **平台**：21财经
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取21财经24小时快讯新闻列表，包括标题、内容、发布时间、链接等

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `page` | string | ✗ | 页码，默认第1页, 默认: `1` |

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
    "spider_name": "21jingji_quick_news",
    "params": {{ ... }}
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "21jingji_quick_news",
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
