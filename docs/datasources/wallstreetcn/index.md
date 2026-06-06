# 华尔街见闻

## 概览

| 统计项 | 数值 |
| :--- | :--- |
| **平台标识** | `wallstreetcn` |
| **接口数量** | 1 |

## 接口列表

| 接口说明 | 爬虫名称 | 版本 |
| :--- | :--- | :---: |
| [获取华尔街见闻7x24小时快讯新闻列表，支持多频道筛选（要闻/A股/美股/港股/外汇/商品/债券/科技），包括标题、内容、发布时间、链接等](wallstreetcn_global_news.md) | `wallstreetcn_global_news` | 1.1.0 |

## 使用说明

所有接口均通过统一的 API 端点调用：

```bash
POST http://localhost:8380/api/v1/spiders/run
```
