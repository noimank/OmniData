




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




