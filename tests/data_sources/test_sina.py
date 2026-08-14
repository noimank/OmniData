from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / ".env")


import pytest

from omnidata.core.browser_context_pool import BrowserContextPool
from omnidata.core import get_spider_register, spider_register, close_spider_register
from omnidata.core.config import BrowserConfig
from omnidata.data_sources.sina.realtime_quote import RealtimeQuoteSpider


@pytest.fixture
async def browser_pool():
    """创建浏览器上下文池实例, 完成环境初始"""
    # 关闭无头模式
    pool = BrowserContextPool(BrowserConfig(headless=False))
    await pool.initialize()

    # 初始化爬虫注册器
    spider_reg = get_spider_register()
    await spider_reg.initialize()

    yield pool
    # 清理
    await close_spider_register()
    await pool.shutdown()


class TestSinaSpider:
    """测试浏览器池"""

    async def test_initialize(self, browser_pool):
        """测试初始化"""

        register = spider_register()
        assert register is not None
        print(register.list_spiders())

    async def test_run(self, browser_pool):
        spider_name = "sina_finance_news"
        params = {"page": 1, "page_size": 50, "tag_id": 0}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)

    async def test_run2(self, browser_pool):
        spider_name = "sina_realtime_quote"
        params = {"symbols": "600519,sz000001,sh000001,510050,159919,920002"}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)

    async def test_stock_minline(self, browser_pool):
        spider_name = "sina_stock_minline"
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        # 现行格式（近期交易日）
        res = await instance.run({"symbol": "600519", "date": "2026-08-13"})
        print(res)
        assert res.success
        data = res.data
        assert data["证券代码"] == "600519"
        assert data["证券名称"] == "贵州茅台"
        assert data["分钟数"] == 241
        assert len(data["分时"]) == 241
        assert data["分时"][0]["时间"] == "09:30"
        assert data["分时"][120]["时间"] == "11:30"
        assert data["分时"][121]["时间"] == "13:01"
        assert data["分时"][-1]["时间"] == "15:00"

    async def test_stock_minline_legacy(self, browser_pool):
        spider_name = "sina_stock_minline"
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        # 早期格式（2020 年历史数据，午间边界为 11:29→13:00）
        res = await instance.run({"symbol": "sh600519", "date": "2020-01-06"})
        print(res)
        assert res.success
        data = res.data
        assert data["分钟数"] == 241
        assert data["分时"][0]["时间"] == "09:30"
        assert data["分时"][119]["时间"] == "11:29"
        assert data["分时"][120]["时间"] == "13:00"
        assert data["分时"][-1]["时间"] == "15:00"

    async def test_stock_minline_no_trading_day(self, browser_pool):
        spider_name = "sina_stock_minline"
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        # 非交易日（周六）
        res = await instance.run({"symbol": "600519", "date": "2026-08-15"})
        print(res)
        assert not res.success
        assert "无分时数据" in res.message
