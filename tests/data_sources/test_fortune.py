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


class TestFortuneSpider:
    """测试 Fortune 新闻快讯爬虫"""

    async def test_initialize(self, browser_pool):
        """测试初始化与自动注册"""

        register = spider_register()
        assert register is not None
        spider_names = register.list_spiders()
        assert "fortune_flash_news" in spider_names

    async def test_run(self, browser_pool):
        """测试爬虫运行与结果解析"""

        spider_name = "fortune_flash_news"
        params = {"num": 5}
        register = spider_register()
        instance = register.get_spider_instance(spider_name)
        res = await instance.run(params)
        print(res)
