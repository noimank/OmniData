"""
OmniData - A scalable web scraping framework
"""

__version__ = "0.1.0"

from omnidata.core import (
    BaseWebSpider,
    BrowserContextPool,
    get_browser_context_pool,
    get_spider_register,
    spider_register,
)

__all__ = [
    "__version__",
    "BaseWebSpider",
    "BrowserContextPool",
    "get_browser_context_pool",
    "spider_register",
    "get_spider_register",
]
