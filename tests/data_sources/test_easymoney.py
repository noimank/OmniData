




import pytest

from omnidata.core.browser_pool import BrowserPool, close_browser_pool, get_browser_pool
from omnidata.core import get_spider_register, spider_register
from omnidata.core.config import  BrowserConfig

@pytest.fixture
async def browser_pool():
    """创建浏览器池实例, 完成环境初始"""
    # 关闭无头模式
    pool = BrowserPool(BrowserConfig(headless=False))
    await pool.initialize()
    await get_spider_register(pool)
    yield pool
    await pool.shutdown()


class TestEastMoneySpider:
    """测试浏览器池"""

    async def test_initialize(self, browser_pool):
        """测试初始化"""

        register = spider_register()
        assert register is not None
        print(register.list_spiders())

    async def test_run(self,browser_pool):
        spider_name = "eastmoney_news_spider"
        params = {"category": "music", "limit": 5}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)

    async def test_run2(self,browser_pool):
        spider_name = "eastmoney_market_flow"
        params = {"day":  40}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)
    async def test_run3(self,browser_pool):
            spider_name = "eastmoney_search"
            params = {"keyword":  "666撒旦解放", "search_type": "qa"}
            register = spider_register()
            instance = register.get_spider_instance(spider_name)
            res = await instance.run(params)
            print(res)

    async def test_run4(self, browser_pool):
        spider_name = "eastmoney_industry_sector_flow"
        params = {"limit": 10, "sort_field": "f62"}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)


    async def test_run5(self, browser_pool):
        spider_name = "eastmoney_concept_sector_flow"
        params = {"limit": 10, "rank_type": "10日"}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)

    async def test_run6(self, browser_pool):
        spider_name = "eastmoney_realtime_stock_fund_flow"
        params = {"secid": '0.000001', "data_format": "json"}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)


    async def test_run7(self, browser_pool):
        spider_name = "eastmoney_stock_history_flow"
        params = {"stock_code": '000001', "limit": 1}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)

    async def test_run8(self, browser_pool):
        spider_name = "eastmoney_stock_intraday_flow"
        params = {"stock_code": '000001', "limit": 1}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)
    async def test_run9(self, browser_pool):
        spider_name = "eastmoney_stock_quote"
        params = {"stock_code": '600798'}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)
    async def test_run10(self, browser_pool):
        spider_name = "eastmoney_margin_trading"
        params = {"market": 'sz', "limit": 10, "data_format": "json"}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)

    async def test_run11(self, browser_pool):
        spider_name = "eastmoney_china_cpi"
        params = {"limit": 10}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)




