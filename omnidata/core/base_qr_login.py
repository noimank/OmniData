"""
二维码登录基类模块
"""

import asyncio
import logging
from abc import abstractmethod
from datetime import datetime, timedelta
from typing import Any, Literal

from playwright.async_api import Page
from pydantic import BaseModel, Field

from .base_helper import BaseHelper
from .browser_pool import BrowserPool

logger = logging.getLogger(__name__)


class QRLoginState(BaseModel):
    status: Literal["waiting", "success", "failed", "not_logged_in"] = Field(description="二维码登录状态")
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
                await self.browser_pool.save_context_state(self._qr_context, "login:eastmoney")

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
                async with self.get_page_context() as page:
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

    # 二维码登录专用的 context 和 page（由 get_qrcode 和 verify_login_state 共用）
    _qr_context: Any = None
    _qr_page: Page | None = None
    _refresh_task: asyncio.Task | None = None
    _running: bool = False
    _last_refresh_time: datetime | None = None
    _refresh_interval: timedelta = timedelta(hours=1)
    _stop_event: asyncio.Event | None = None

    def __init__(self, browser_pool: BrowserPool | None = None, config: Any | None = None):
        super().__init__(browser_pool, config)
        self._start_refresh_task()

    def _start_refresh_task(self) -> None:
        """启动后台刷新任务"""
        if self._running:
            return

        self._running = True
        self._stop_event = asyncio.Event()
        self._last_refresh_time = datetime.now()

        async def refresh_loop():
            """每小时刷新一次登录状态"""
            while self._running:
                await asyncio.sleep(1)

                # 收到停止信号，退出循环
                if self._stop_event.is_set():
                    break

                if self._running:
                    now = datetime.now()
                    elapsed = now - self._last_refresh_time

                    if elapsed >= self._refresh_interval:
                        try:
                            await self.refresh_login_state()
                            logger.info(f"{datetime.now().isoformat()}->刷新 {self.platform} 平台的登录状态成功！")
                            self._last_refresh_time = now
                        except Exception as e:
                            logger.error(f"Error in refresh task: {e}")

        self._refresh_task = asyncio.create_task(refresh_loop())

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
            可通过 self.get_page_context() 获取独立的页面上下文
        """
        raise NotImplementedError

    async def close(self) -> None:
        """清理资源"""

        if self._qr_page and not self._qr_page.is_closed():
            await self._qr_page.close()

        if self._qr_context:
            await self._qr_context.close()

        self._qr_context = None
        self._qr_page = None

    async def destroy(self) -> None:
        """销毁实例，停止后台刷新任务并清理资源"""
        # 1. 停止后台刷新任务
        self._running = False
        if self._stop_event:
            self._stop_event.set()

        # 2. 等待任务完成
        if self._refresh_task and not self._refresh_task.done():
            try:
                await asyncio.wait_for(self._refresh_task, timeout=5.0)
            except (TimeoutError, asyncio.CancelledError):
                # 如果任务没有正常退出，取消它
                if not self._refresh_task.done():
                    self._refresh_task.cancel()
                    try:
                        await self._refresh_task
                    except asyncio.CancelledError:
                        pass

        # 3. 清理浏览器资源
        await self.close()

        # 4. 清理引用
        self._refresh_task = None
        self._stop_event = None

    @classmethod
    def get_info(cls) -> dict[str, Any]:
        """获取登录器信息"""
        return {
            "name": cls.name or cls.__name__,
            "description": cls.description,
            "version": cls.version,
            "author": cls.author,
            "platform": cls.platform,
        }
