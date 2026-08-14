"""
二维码登录基类模块
"""

import asyncio
import base64
import logging
from abc import abstractmethod
from typing import Any, Literal

from playwright.async_api import Page
from pydantic import BaseModel, Field

from .base_helper import BaseHelper
from .browser_context_pool import BrowserContextPool

logger = logging.getLogger(__name__)


class QRLoginState(BaseModel):
    status: Literal["waiting", "success", "failed", "not_logged_in"] = Field(
        description="二维码登录状态"
    )
    message: str = Field(default="", description="登录状态描述")


class QRCode(BaseModel):
    success: bool = Field(default=True, description="是否成功获取二维码")
    url: str = Field(default="", description="二维码资源地址")
    qr_type: str = Field(default="", description="二维码登录类型")
    message: str = Field(default="", description="描述信息")


class BaseQRLogin(BaseHelper):
    """
    二维码登录基类

    子类需要实现以下抽象方法：
        1. refresh_login_state(): 重新保存登录状态到 Redis
        2. get_qrcode(qr_type): 获取指定类型的二维码
        3. verify_login_state(): 验证二维码登录是否完成（与 get_qrcode 共用 page/context）
        4. is_login(): 验证是否已登录（使用独立的 page/context）

    示例:
        ```python
        class EastMoneyLogin(BaseQRLogin):
            name = "eastmoney_login"
            platform = "eastmoney"

            async def refresh_login_state(self) -> None:
                # 重新保存登录状态到 Redis
                await self.browser_context_pool.save_context_state(self._qr_context, "login:eastmoney")

            async def get_qrcode(self, qr_type: str) -> dict:
                # 获取二维码，使用 self._qr_page 和 self._qr_context
                await self._qr_page.goto("https://example.com/login")
                return {"qr_url": "https://example.com/qrcode"}

            async def verify_login_state(self) -> dict:
                # 验证登录状态，使用 self._qr_page 和 self._qr_context
                is_logged_in = await self._qr_page.query_selector(".user-avatar") is not None
                return {"status": "success" if is_logged_in else "pending"}

            async def is_login(self) -> bool:
                # 使用独立的 page/context 验证是否已登录
                async with self.new_page(namespace="eastmoney") as page:
                    await page.goto("https://example.com")
                    return await page.query_selector(".user-avatar") is not None
        ```
    """

    # name就是浏览器context中的namespace，注意了
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    platform: str = ""

    def __init__(
        self, browser_context_pool: BrowserContextPool | None = None, config: Any | None = None
    ):
        super().__init__(browser_context_pool, config)
        # 二维码登录专用的 context 和 page（由 get_qrcode 和 verify_login_state 共用）
        # 实例变量，避免类变量共享
        self._qr_context: Any = None
        self._qr_page: Page | None = None
        # 保护 _qr_page 生命周期，防止并发 get_qrcode 产生孤儿 page
        self._lock = asyncio.Lock()
        # 登录状态缓存
        self._login_status = QRLoginState(status="not_logged_in", message="默认未登录状态")

    @abstractmethod
    async def refresh_login_state(self) -> None:
        """
        重新保存登录状态到 Redis

        子类必须实现此方法，用于定期刷新登录状态到 Redis。
        """
        raise NotImplementedError

    @abstractmethod
    async def get_qrcode(self, qr_type: str) -> QRCode:
        """
        获取指定类型的二维码

        Args:
            qr_type: 二维码类型

        Returns:
            包含二维码信息的字典，如 {"qr_url": "...", "qr_id": "..."}

        注意:
            使用 self._qr_page 和 self._qr_context 进行操作
        """
        raise NotImplementedError

    @abstractmethod
    async def get_qrcode_types(self) -> list:
        """
        获取支持的二维码类型

        Returns:
            包含二维码类型的数组，如 ["微信", "QQ"]
        """
        raise NotImplementedError

    @abstractmethod
    async def verify_login_state(self) -> QRLoginState:
        """
        验证二维码登录是否完成

        Returns:
            包含登录状态的字典，如 {"status": "success", "message": "状态描述"}
            状态类型有：

        注意:
            与 get_qrcode 共用 self._qr_page 和 self._qr_context
        """
        raise NotImplementedError

    @abstractmethod
    async def is_login(self) -> QRLoginState:
        """
        验证是否已登录

        Returns:
            是否已登录

        注意:
            使用独立的 page/context，与 get_qrcode 和 verify_login_state 分离
            可通过 self.new_page(namespace) 获取独立的页面上下文
        """
        raise NotImplementedError

    def set_login_status(self, status_info: QRLoginState) -> None:
        """
        设置登录状态缓存

        Args:
            status_info: 登录状态信息
        """
        self._login_status = status_info

    def get_login_status(self) -> QRLoginState:
        """
        获取缓存的登录状态

        Returns:
            缓存的登录状态（实例创建后默认为 not_logged_in）
        """
        return self._login_status

    def _qr_page_alive(self) -> bool:
        """
        二维码会话页面是否仍然可用。

        处理浏览器池回收后残留的悬空引用（page 已被池关闭但引用未清空）。
        """
        return self._qr_page is not None and not self._qr_page.is_closed()

    def has_active_qr_session(self) -> bool:
        """是否存在进行中的二维码登录会话（供刷新任务判断是否可安全清理）"""
        return self._qr_page_alive()

    async def close(self) -> None:
        """清理资源（幂等，可安全重复调用；对已被池关闭的 page 同样安全）"""

        # 关闭 page
        if self._qr_page is not None:
            try:
                if not self._qr_page.is_closed():
                    await self._qr_page.close()
            except Exception:
                pass  # page 可能已经被关闭（如浏览器池回收）

        self._qr_page = None
        # 不再引用context，但是不关闭
        self._qr_context = None

    async def destroy(self) -> None:
        """销毁实例，清理浏览器资源

        注意：后台刷新任务已由 LoginRegister 统一管理，此处不再处理任务停止。
        """
        # 清理浏览器资源
        await self.close()

    @classmethod
    def get_info(cls) -> dict[str, Any]:
        """获取登录器基本信息（类方法）"""
        return {
            "name": cls.name or cls.__name__,
            "description": cls.description,
            "version": cls.version,
            "author": cls.author,
            "platform": cls.platform,
        }

    async def screenshot_element_to_base64(self, page: Page, selector: str) -> str:
        """
        截取页面元素并转换为 Base64 编码的 Data URI
        受 https://github.com/noimank/OmniData/issues/1 启发，有些平台二维码二次访问会变化，进而采用截图的方式保证二维码的一致性

        Args:
            page: Playwright Page 实例
            selector: 元素选择器

        Returns:
            Base64 编码的 Data URI，格式：data:image/png;base64,iVBORw0KG...

        Raises:
            Exception: 截图失败时抛出异常
        """
        try:
            # 定位元素
            element = page.locator(selector)
            await element.wait_for(state="visible", timeout=5000)

            # 截图并获取字节数据
            screenshot_bytes = await element.screenshot(type="png")

            # 转换为 Base64
            image_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            # 返回 Data URI 格式
            return f"data:image/png;base64,{image_base64}"

        except Exception as e:
            logger.error(f"Failed to screenshot element {selector}: {e}")
            raise Exception(f"截图元素失败: {str(e)}")
