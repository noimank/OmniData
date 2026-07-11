from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / ".env")


import pytest

from omnidata.core.browser_context_pool import BrowserContextPool
from omnidata.core import get_spider_register, spider_register, close_spider_register
from omnidata.core.config import BrowserConfig


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


class TestInvesTingSpider:
    """测试浏览器池"""

    async def test_initialize(self, browser_pool):
        """测试初始化"""

        register = spider_register()
        assert register is not None
        print(register.list_spiders())

    async def test_run1(self, browser_pool):
        spider_name = "xueqiu_flash_news"
        params = {"limit": 20}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)
