"""
OmniData Core Module
提供爬虫框架的核心功能
"""

from .base_qr_login import BaseQRLogin, QRCode, QRLoginState
from .base_web_spider import BaseWebSpider, SpiderResult
from .browser_context_pool import (
    BrowserContextPool,
    close_browser_context_pool,
    get_browser_context_pool,
)
from .login_register import (
    close_login_register,
    get_login_register,
    login_register,
)
from .spider_register import (
    close_spider_register,
    get_spider_register,
    spider_register,
)

__all__ = [
    "BaseWebSpider",
    "SpiderResult",
    "BrowserContextPool",
    "get_browser_context_pool",
    "close_browser_context_pool",
    "spider_register",
    "get_spider_register",
    "close_spider_register",
    "BaseQRLogin",
    "get_login_register",
    "login_register",
    "close_login_register",
    "QRLoginState",
    "QRCode",
]
