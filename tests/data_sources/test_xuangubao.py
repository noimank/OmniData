from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / ".env")


import pytest

from omnidata.core.browser_context_pool import BrowserContextPool
from omnidata.core import get_spider_register, spider_register, close_spider_register
from omnidata.core.config import BrowserConfig


@pytest.fixture
async def browser_pool():
    """创建浏览器上下文池实例"""
    pool = BrowserContextPool(BrowserConfig(headless=False))
    await pool.initialize()

    spider_reg = get_spider_register()
    await spider_reg.initialize()

    yield pool

    await close_spider_register()
    await pool.shutdown()


class TestXuanguBaoSpider:
    """选股宝快讯爬虫集成测试"""

    async def test_initialize(self, browser_pool):
        """测试爬虫注册"""
        register = spider_register()
        assert register is not None
        spider = register.get_spider_instance("xuangubao_flash_news")
        assert spider is not None

    async def test_fetch_flash_news(self, browser_pool):
        """测试获取快讯"""
        register = spider_register()
        instance = register.get_spider_instance("xuangubao_flash_news")
        res = await instance.run({"limit": 10})
        print(res)
        assert res.success is True
        assert res.data is not None
        assert res.data["total"] > 0
        assert len(res.data["news_list"]) > 0

        item = res.data["news_list"][0]
        assert "title" in item
        assert "content" in item
        assert "pub_time" in item
        assert "url" in item
