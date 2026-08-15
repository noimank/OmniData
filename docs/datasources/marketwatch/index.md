# 市场观察

## 概览

| 统计项 | 数值 |
| :--- | :--- |
| **平台标识** | `marketwatch` |
| **接口数量** | 1 |

## 接口列表

| 接口说明 | 爬虫名称 | 版本 |
| :--- | :--- | :---: |
| [聚合 MarketWatch 四个官方 feed 获取最新新闻快讯，按时间倒序，包括标题、摘要、作者、发布时间、链接等](marketwatch_flash_news.md) | `marketwatch_flash_news` | 1.1.0 |

## 使用说明

所有接口均通过统一的 API 端点调用：

```bash
POST http://localhost:8380/api/v1/spiders/run
```
