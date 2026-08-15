# 财富

## 概览

| 统计项 | 数值 |
| :--- | :--- |
| **平台标识** | `fortune` |
| **接口数量** | 1 |

## 接口列表

| 接口说明 | 爬虫名称 | 版本 |
| :--- | :--- | :---: |
| [获取 Fortune 最新新闻快讯，包括标题、摘要、发布时间、链接等](fortune_flash_news.md) | `fortune_flash_news` | 1.0.0 |

## 使用说明

所有接口均通过统一的 API 端点调用：

```bash
POST http://localhost:8380/api/v1/spiders/run
```
