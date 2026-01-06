"""
OmniData - A scalable web scraping framework
"""

__version__ = "0.1.0"

from omnidata.core import (
    BaseWebSpider,
    BrowserPool,
    get_browser_pool,
    get_spider_register,
    spider_register,
)

__all__ = [
    "__version__",
    "BaseWebSpider",
    "BrowserPool",
    "get_browser_pool",
    "spider_register",
    "get_spider_register",
]
