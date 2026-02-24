# 同花顺问财

同花顺智能搜索接口。

---

## 接口概览

[![智能搜索](https://img.shields.io/badge/智能搜索-yellowgreen)](javascript:)

---

## 特点

- 支持自然语言查询
- 无需登录

---

## 使用示例

```bash
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "ths_iwencai_search",
    "params": {
      "query": "市盈率小于20的银行股"
    }
  }'
```

### 自然语言查询示例

| 查询 | 说明 |
| :--- | :--- |
| `市盈率小于20的银行股` | 筛选低估值银行股 |
| `昨天涨停的股票` | 获取昨日涨停股票列表 |
| `ROE大于15的消费股` | 高ROE消费股 |
| `流通市值小于50亿的科技股` | 小盘科技股 |
