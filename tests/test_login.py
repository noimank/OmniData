from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量测试
load_dotenv(Path(__file__).parent.parent / ".env")

import pytest

from omnidata.core import login_register
from omnidata.core.browser_context_pool import BrowserContextPool
from omnidata.core import get_login_register, close_spider_register
from omnidata.core.config import BrowserConfig


@pytest.fixture
async def browser_pool():
    """创建浏览器上下文池实例, 完成环境初始"""
    # 关闭无头模式
    # 关闭无头模式
    pool = BrowserContextPool(BrowserConfig(headless=False))
    await pool.initialize()

    # 初始化爬虫注册器
    login_reg = get_login_register()
    await login_reg.initialize()

    yield pool
    # 清理
    await close_spider_register()
    await pool.shutdown()


class TestLogin:
    """测试浏览器池"""

    async def test_initialize(self, browser_pool):
        """测试初始化"""

        register = login_register()
        assert register is not None
        print(register.list_logins())

    async def test_bilibili(self, browser_pool):
        login_name = "bilibili"
        register = login_register()
        instance = register.get_login_instance(login_name)
        # res = await instance.get_qrcode("哔哩哔哩官方")
        # res = await instance.get_qrcode("微信")
        res = await instance.is_login()

        print(res)

    async def test_eastmoney(self, browser_pool):
        login_name = "eastmoney"
        register = login_register()
        instance = register.get_login_instance(login_name)
        res = await instance.get_qrcode("东方财富官方")
        # res = await instance.get_qrcode("微信")
        # res = await instance.is_login()

        print(res)

    async def test_ths_10jqks(self, browser_pool):
        login_name = "ths_10jqka"
        register = login_register()
        instance = register.get_login_instance(login_name)
        res = await instance.get_qrcode("同花顺APP")
        # res = await instance.get_qrcode("微信")
        # res = await instance.is_login()

        print(res)

    async def test_ths_iwencai(self, browser_pool):
        login_name = "ths_iwencai"
        register = login_register()
        instance = register.get_login_instance(login_name)
        # res = await instance.get_qrcode("同花顺APP")
        # res = await instance.get_qrcode("微信")
        res = await instance.is_login()
        # res = await instance.verify_login_state()

        print(res)
