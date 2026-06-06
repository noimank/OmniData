# 获取格隆汇7x24实时财经快讯，包括内容、时间、链接、相关股票等

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `gelonghui_flash_news` |
| **平台** | 格隆汇 |
| **版本** | 1.0.0 |
| **作者** | noimank |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `limit` | `int` | ✗ | `20` | 获取快讯数量，默认20条，最大50条 |
| `channel` | `str` | ✗ | `all` | 频道ID：all(全部), popular(最热), international(国际), AStock(A股), HKStock(港股), USStock(美股), exchangeCommodity(商品外汇), ai(AI), fundLive(基金), debenture(债券), virtualAssets(虚拟资产) |

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run   -H "Content-Type: application/json"   -d '{
    "spider_name": "gelonghui_flash_news",
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
            "spider_name": "gelonghui_flash_news",
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
