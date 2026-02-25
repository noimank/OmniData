# 数据源

OmniData 支持 15+ 个数据源平台，提供 30+ 个数据接口。

---

## 平台列表

| 平台 | 接口数 | 类别 |
| :--- | :---: | :--- |
| [东方财富](eastmoney/index.md) | 19 | 金融行情 |
| [Bilibili](bilibili/index.md) | 1 | 视频 |
| [财联社](cls/index.md) | 1 | 全球新闻 |
| [富途牛牛](futunn/index.md) | 1 | 快讯 |
| [和讯网](hexun/index.md) | 1 | 7x24 快讯 |
| [金融界](jrj/index.md) | 1 | 快讯 |
| [21财经](21jingji/index.md) | 1 | 快讯 |
| [第一财经](yicai/index.md) | 1 | 快讯 |
| [华尔街见闻](wallstreetcn/index.md) | 1 | 全球快讯 |
| [新浪财经](sina/index.md) | 1 | 国际新闻 |
| [同花顺](ths_10jqka/index.md) | 1 | 资讯 |
| [同花顺问财](ths_iwencai/index.md) | 1 | 智能搜索 |

---

## 接口分类

### 金融行情

- 股票行情
- K 线数据
- 资金流向
- 龙虎榜
- 融资融券

### 新闻资讯

- 7x24 快讯
- 全球新闻
- 财经资讯

### 其他

- 视频信息（Bilibili）
- 智能搜索（同花顺问财）

---

## 使用方式

### 通过 API

```bash
# 列出所有爬虫
curl http://localhost:8380/spiders

# 运行爬虫
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "eastmoney_stock_quote",
    "params": {"secucode": "000001"}
  }'
```

### 通过 MCP

创建 MCP 服务后，所有爬虫自动暴露为 MCP 工具。

---

## 添加新数据源

详见 [创建爬虫](../development/creating-spider.md)。

---

选择平台查看具体接口文档。
