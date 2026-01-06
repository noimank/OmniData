from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量测试
load_dotenv(Path(__file__).parent.parent / ".env")

import pytest

from omnidata.core.browser_pool import BrowserPool
from omnidata.core import get_login_register, login_register
from omnidata.core.config import settings


@pytest.fixture
async def browser_pool():
    """创建浏览器池实例, 完成环境初始"""
    # 关闭无头模式
    pool = BrowserPool(settings.browser)
    await pool.initialize()
    await get_login_register(pool)
    yield pool
    await pool.shutdown()


class TestLogin:
    """测试浏览器池"""

    async def test_initialize(self, browser_pool):
        """测试初始化"""

        register = login_register()
        assert register is not None
        print(register.list_logins())

    async def test_bilibili(self, browser_pool):
        login_name = "bilibili_qr_login"
        register = login_register()
        instance = register.get_login_instance(login_name)
        # res = await instance.get_qrcode("哔哩哔哩官方")
        # res = await instance.get_qrcode("微信")
        res = await instance.is_login()



        print(res)
