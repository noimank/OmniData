# 获取同花顺全球财经快讯新闻列表，支持按标签筛选（全部/要闻/A股/港股/美股/基金/观点/公告）

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `ths_10jqka_global_news` |
| **平台** | 同花顺10jqka |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `page` | `int` | ✗ | `1` | 页码，默认第1页 |
| `tag` | `str` | ✗ | `21101` | 标签筛选，支持的数字ID: 21101=全部(默认), -21101=要闻, 21103=A股, 21105=港股, 21107=美股, 21109=基金, 21111=观点, 34843=公告 |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "ths_10jqka_global_news",
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
            "spider_name": "ths_10jqka_global_news",
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
