"""
测试全局夹具

pytest-asyncio 为每个测试创建独立事件循环，而全局 BrowserContextPool
单例会跨测试存活：playwright 驱动绑定在首个使用它的循环上，该循环关闭后
浏览器对象残留（is_connected 仍为 True），后续测试会拿到死浏览器
（Browser.new_context: 'NoneType' object has no attribute 'send'）。

每个测试结束后重置全局池，保证下一个测试在自己的循环上全新初始化。
"""

import pytest

from omnidata.core.browser_context_pool import close_browser_context_pool


@pytest.fixture(autouse=True)
async def _reset_global_browser_pool():
    """测试间重置全局浏览器池（autouse，teardown 在各文件级夹具之后执行）"""
    yield
    await close_browser_context_pool()
