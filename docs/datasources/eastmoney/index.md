# 东方财富

## 概览

| 统计项 | 数值 |
| :--- | :--- |
| **平台标识** | `eastmoney` |
| **接口数量** | 27 |

## 接口列表

| 接口说明 | 爬虫名称 | 版本 |
| :--- | :--- | :---: |
| [获取指定日期范围的龙虎榜活跃营业部数据，包括营业部买卖金额、净买入额、上榜次数等](eastmoney_active_department.md) | `eastmoney_active_department` | 1.0.0 |
| [获取概念板块资金流向排行数据，支持今日、5日、10日排行查询](eastmoney_concept_sector_flow.md) | `eastmoney_concept_sector_flow` | 1.0.0 |
| [获取中国CPI居民消费价格指数月度数据，包括全国、城市、农村的当月同比、环比增长及累计数据](eastmoney_china_cpi.md) | `eastmoney_china_cpi` | 1.0.0 |
| [获取指定日期范围的龙虎榜交易明细数据，包括上榜股票、涨跌幅、龙虎榜买卖金额等](eastmoney_daily_billboard_details.md) | `eastmoney_daily_billboard_details` | 1.0.0 |
| [获取营业部收益率排行榜数据，包括营业部上榜次数、收益率、交易金额等](eastmoney_department_return_ranking.md) | `eastmoney_department_return_ranking` | 1.0.0 |
| [获取ETF基金持仓明细数据，包括持仓股票、占净值比例、持股数、持仓市值等信息，支持按年份筛选](eastmoney_etf_holdings.md) | `eastmoney_etf_holdings` | 1.0.0 |
| [获取东方财富全球财经快讯新闻列表，包括标题、摘要、时间、评论数、分享数等](eastmoney_fast_news.md) | `eastmoney_fast_news` | 1.0.0 |
| [获取基金（ETF/LOF/普通基金等）的行业配置数据，包括行业类别、占净值比例、市值、行业变动详情链接等信息，支持按年份筛选（最新年份仅返回当前报告期，历史年份返回该年度所有季度报告）](eastmoney_fund_industry_allocation.md) | `eastmoney_fund_industry_allocation` | 1.0.0 |
| [获取ETF/LOF基金历史净值数据，包括单位净值、累计净值、日增长率、申赎状态、分红送配等信息，支持日期范围筛选](eastmoney_fund_nav_history.md) | `eastmoney_fund_nav_history` | 1.0.0 |
| [获取指定行业板块的历史资金流向数据（日线/周线/月线）](eastmoney_industry_history_flow.md) | `eastmoney_industry_history_flow` | 1.0.0 |
| [获取指定行业板块的实时资金流向数据（分钟级）](eastmoney_industry_realtime_flow.md) | `eastmoney_industry_realtime_flow` | 1.0.0 |
| [获取行业板块最新资金流向排行数据](eastmoney_industry_sector_flow.md) | `eastmoney_industry_sector_flow` | 1.0.0 |
| [获取沪深北三市融资融券历史数据，支持查询全部/沪市/深市/京市，支持1日/3日/5日/10日统计周期](eastmoney_margin_trading.md) | `eastmoney_margin_trading` | 1.1.0 |
| [获取沪深两市大盘资金流向历史数据](eastmoney_market_flow.md) | `eastmoney_market_flow` | 1.0.0 |
| [获取个股、指数、ETF基金的实时资金流向数据，包括主力、超大单、大单、中单、小单的净流入及占比，以及5日、10日累计资金流向](eastmoney_realtime_stock_fund_flow.md) | `eastmoney_realtime_stock_fund_flow` | 1.0.0 |
| [东方财富网通用搜索，支持资讯、公告、研报、问董秘四种搜索类型](eastmoney_search.md) | `eastmoney_search` | 1.0.0 |
| [获取指定行业板块内个股的资金流向排行数据](eastmoney_sector_stock_flow.md) | `eastmoney_sector_stock_flow` | 1.0.0 |
| [获取A股个股历史龙虎榜上榜数据，包括上榜原因、涨跌幅、买卖金额、营业部净买入以及上榜后多日涨跌幅等完整数据，支持日期范围查询](eastmoney_stock_billboard.md) | `eastmoney_stock_billboard` | 1.0.0 |
| [获取A股/ETF筹码分布数据，包括获利比例、平均成本、90%/70%筹码集中度等指标，用于分析筹码结构和成本分布](eastmoney_stock_chip_distribution.md) | `eastmoney_stock_chip_distribution` | 1.0.0 |
| [获取A股/ETF基金历史日线K线数据，包括开高低收、成交量成交额、涨跌幅等完整K线数据，支持前复权/后复权/不复权，支持日期范围查询](eastmoney_stock_daily_kline.md) | `eastmoney_stock_daily_kline` | 1.1.0 |
| [获取个股/ETF历史资金流向数据](eastmoney_stock_history_flow.md) | `eastmoney_stock_history_flow` | 1.0.0 |
| [获取个股/ETF分时资金流向数据（分钟级别），包括主力、超大单、大单、中单、小单的净流入](eastmoney_stock_intraday_flow.md) | `eastmoney_stock_intraday_flow` | 1.0.0 |
| [获取沪深京A股实时行情列表数据，支持分页和排序](eastmoney_stock_list.md) | `eastmoney_stock_list` | 1.0.0 |
| [获取单只股票的融资融券历史数据，支持1日/3日/5日/10日统计周期](eastmoney_stock_margin_trading.md) | `eastmoney_stock_margin_trading` | 1.0.0 |
| [获取单只股票的机构买卖统计数据，包括龙虎榜机构交易明细、买卖金额、上榜原因等](eastmoney_stock_organization_trade.md) | `eastmoney_stock_organization_trade` | 1.0.0 |
| [获取A股/ETF基金实时行情报价数据，包括最新价、涨跌幅、成交量、成交额、买卖五价、市值、市盈率等完整行情数据](eastmoney_stock_quote.md) | `eastmoney_stock_quote` | 1.2.0 |
| [东方财富条件选股，通过自然语言查询获取符合条件的股票列表](eastmoney_stock_selection.md) | `eastmoney_stock_selection` | 2.0.0 |

## 使用说明

所有接口均通过统一的 API 端点调用：

```bash
POST http://localhost:8380/api/v1/spiders/run
```
