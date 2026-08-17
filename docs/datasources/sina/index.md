# 新浪财经

## 概览

| 统计项 | 数值 |
| :--- | :--- |
| **平台标识** | `sina` |
| **接口数量** | 4 |

## 接口列表

| 接口说明 | 爬虫名称 | 版本 |
| :--- | :--- | :---: |
| [获取新浪财经7x24小时全球财经快讯，支持按标签筛选（全部/宏观/公司/数据/市场/观点/央行/其他/A股/国际）](sina_finance_news.md) | `sina_finance_news` | 1.0.0 |
| [批量获取多只股票/指数/ETF实时行情报价，包括最新价、涨跌额、涨跌幅、成交量、成交额、振幅、买卖五档盘口等，免登录免Key，浏览器请求自动分批](sina_realtime_quote.md) | `sina_realtime_quote` | 1.0.0 |
| [获取个股/ETF指定交易日的分时数据（分钟级价格/均价/成交量），可查询任意历史交易日，](sina_stock_minline.md) | `sina_stock_minline` | 1.0.0 |
| [获取个股/ETF当日实时分时数据（分钟级开盘/最高/最低/收盘/成交量/成交额），盘中即可获取，](sina_stock_minline_realtime.md) | `sina_stock_minline_realtime` | 1.0.0 |

## 使用说明

所有接口均通过统一的 API 端点调用：

```bash
POST http://localhost:8380/api/v1/spiders/run
```
