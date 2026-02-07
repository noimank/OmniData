
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent.parent / ".env")



import pytest

from omnidata.core.browser_context_pool import BrowserContextPool
from omnidata.core import set_spider_register, spider_register
from omnidata.core.config import  BrowserConfig

@pytest.fixture
async def browser_pool():
    """创建浏览器上下文池实例, 完成环境初始"""
    # 关闭无头模式
    pool = BrowserContextPool(BrowserConfig(headless=False))
    await pool.initialize()

    # 初始化爬虫注册器
    from omnidata.core.spider_register import SpiderRegister
    spider_reg = SpiderRegister(pool)
    await spider_reg.initialize()
    set_spider_register(spider_reg)

    yield pool
    await pool.shutdown()


class TestJRJSpider:
    """测试浏览器池"""

    async def test_initialize(self, browser_pool):
        """测试初始化"""

        register = spider_register()
        assert register is not None
        print(register.list_spiders())

    async def test_run(self,browser_pool):
        spider_name = "jrj_news_flash"
        params = { "page_size": 50}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)
