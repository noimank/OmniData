"""
OmniData Core Module
提供爬虫框架的核心功能
"""

from .base_web_spider import BaseWebSpider
from .browser_pool import BrowserPool, get_browser_pool
from .spider_register import get_spider_register, spider_register
from .base_qr_login import BaseQRLogin, QRLoginState, QRCode
from .login_register import get_login_register, login_register

__all__ = [
    "BaseWebSpider",
    "BrowserPool",
    "get_browser_pool",
    "spider_register",
    "get_spider_register",
    "BaseQRLogin",
    "get_login_register",
    "login_register"
]
