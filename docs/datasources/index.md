# 数据源

## 统计概览

| 统计项 | 数值 |
| :--- | :--- |
| **支持平台数** | 11 |
| **总接口数** | 32 |

## 平台列表

| 平台 | 接口数 | 标识 |
| :--- | :---: | :--- |
| [21财经](21jingji/index.md) | 1 | `21jingji` |
| [财联社](cls/index.md) | 1 | `cls` |
| [东方财富](eastmoney/index.md) | 22 | `eastmoney` |
| [测试平台](example/index.md) | 1 | `example` |
| [富途牛牛](futunn/index.md) | 1 | `futunn` |
| [和讯网](hexun/index.md) | 1 | `hexun` |
| [金融界](jrj/index.md) | 1 | `jrj` |
| [新浪财经](sina/index.md) | 1 | `sina` |
| [同花顺10jqka](ths_10jqka/index.md) | 1 | `ths_10jqka` |
| [华尔街见闻](wallstreetcn/index.md) | 1 | `wallstreetcn` |
| [第一财经](yicai/index.md) | 1 | `yicai` |

## 使用方式

### 通过 API

```bash
curl http://localhost:8380/api/v1/spiders
curl -X POST http://localhost:8380/api/v1/spiders/run -H "Content-Type: application/json" -d '{"spider_name": "xxx"}'
```

### 通过 MCP

创建 MCP 服务后，所有爬虫自动暴露为 MCP 工具。
