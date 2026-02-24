# Jrj News Flash

!!! abstract "接口信息"
    - **爬虫名称**：`jrj_news_flash`
    - **平台**：金融界
    - **作者**：noimank
    - **版本**：1.0.0

## 功能说明

获取金融界24小时快讯新闻列表，包括标题、内容、发布时间、来源、链接等

## 请求参数

该接口无需参数。

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
    "spider_name": "jrj_news_flash"
  }'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={
            "spider_name": "jrj_news_flash"
        }
    )
    result = resp.json()
```

## 注意事项

!!! tip "使用提示"
    具体使用方法请参考代码实现。

!!! warning "限制"
    请合理使用接口，避免频繁请求。
