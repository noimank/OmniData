# 东方财富

东方财富网数据接口，提供股票行情、资金流向、龙虎榜等金融数据。

---

## 接口概览

### 行情数据

[![股票行情](https://img.shields.io/badge/股票行情-blue)](eastmoney_stock_quote.md)
[![日K线](https://img.shields.io/badge/日K线-9cf)](eastmoney_stock_daily_kline.md)
[![股票列表](https://img.shields.io/badge/沪深京A股列表-lightblue)](eastmoney_stock_list.md)

### 资金流向

[![历史资金](https://img.shields.io/badge/历史资金流向-green)](eastmoney_stock_history_flow.md)
[![分时资金](https://img.shields.io/badge/分时资金流向-success)](eastmoney_stock_intraday_flow.md)
[![实时资金](https://img.shields.io/badge/实时资金-important)](eastmoney_realtime_stock_fund_flow.md)
[![市场资金](https://img.shields.io/badge/市场资金流向-informational)](eastmoney_market_flow.md)
[![行业板块](https://img.shields.io/badge/行业板块流向-ff69b4)](eastmoney_industry_sector_flow.md)
[![概念板块](https://img.shields.io/badge/概念板块流向-purple)](eastmoney_concept_sector_flow.md)
[![行业板块个股](https://img.shields.io/badge/板块个股流向-blueviolet)](eastmoney_sector_stock_flow.md)

### 龙虎榜

[![龙虎榜](https://img.shields.io/badge/龙虎牌-red)](eastmoney_stock_billboard.md)
[![龙虎榜详情](https://img.shields.io/badge/龙虎牌详情-critical)](eastmoney_daily_billboard_details.md)
[![机构交易](https://img.shields.io/badge/机构交易-orange)](eastmoney_stock_organization_trade.md)

### 交易数据

[![融资融券](https://img.shields.io/badge/融资融券-teal)](eastmoney_stock_margin_trading.md)
[![融资融券(个股)](https://img.shields.io/badge/个股融资融券-cyan)](eastmoney_margin_trading.md)
[![筹码分布](https://img.shields.io/badge/筹码分布-indigo)](eastmoney_stock_chip_distribution.md)

### 营业部

[![活跃营业部](https://img.shields.io/badge/活跃营业部-yellowgreen)](eastmoney_active_department.md)
[![收益排名](https://img.shields.io/badge/营业部收益排名-yellow)](eastmoney_department_return_ranking.md)

### 其他

[![CPI数据](https://img.shields.io/badge/CPI数据-lightgrey)](eastmoney_china_cpi.md)
[![股票搜索](https://img.shields.io/badge/股票搜索-brightgreen)](eastmoney_search.md)
[![快讯](https://img.shields.io/badge/快讯-ff5722)](eastmoney_fast_news.md)

### 智能选股

[![条件选股](https://img.shields.io/badge/条件选股-9c27b0)](eastmoney_stock_selection.md)

---

## 特点

- 无需登录
- 数据实时更新
- 支持沪深市场

---

## 快速开始

### 获取股票行情

```bash
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "eastmoney_stock_quote",
    "params": {
      "stock_code": "000001"
    }
  }'
```

### 查看市场资金流向

```bash
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "eastmoney_market_flow",
    "params": {}
  }'
```

---

点击上方标签查看详细文档。
