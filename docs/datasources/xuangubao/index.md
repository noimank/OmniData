# 选股宝

## 概览

| 统计项 | 数值 |
| :--- | :--- |
| **平台标识** | `xuangubao` |
| **接口数量** | 1 |

## 接口列表

| 接口说明 | 爬虫名称 | 版本 |
| :--- | :--- | :---: |
| [获取选股宝7x24实时财经快讯，包括内容、时间、链接等](xuangubao_flash_news.md) | `xuangubao_flash_news` | 1.0.0 |

## 使用说明

所有接口均通过统一的 API 端点调用：

```bash
POST http://localhost:8380/api/v1/spiders/run
```
