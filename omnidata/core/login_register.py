"""
登录类注册器模块
"""

import asyncio
import importlib
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any

from .base_qr_login import BaseQRLogin, QRCode
from .browser_pool import BrowserPool, get_browser_pool
from .exceptions import LoginNotFoundError, LoginRegistrationError

logger = logging.getLogger(__name__)


class LoginRegister:
    """登录类注册器"""

    def __init__(self, browser_pool: BrowserPool | None = None):
        self._data_sources_dir = Path(__file__).parent.parent.joinpath("data_sources")
        self._browser_pool = browser_pool
        self._logins: dict[str, type[BaseQRLogin]] = {}
        self._instances: dict[str, BaseQRLogin] = {}
        self._is_initialized = False

    async def initialize(self) -> None:
        if self._is_initialized:
            return

        if self._browser_pool is None:
            self._browser_pool = await get_browser_pool()

        await self._discover_logins()
        self._is_initialized = True

        logger.info(f"LoginRegister initialized with {len(self._logins)} login classes")

    async def shutdown(self) -> None:
        """关闭所有登录实例，取消后台登录保持任务（并发优化版本）"""
        logger.info(f"Shutting down LoginRegister with {len(self._instances)} instances")

        async def destroy_single(name: str, instance: BaseQRLogin) -> None:
            """销毁单个登录实例"""
            try:
                await instance.destroy()
                logger.debug(f"Destroyed login instance: {name}")
            except Exception as e:
                logger.error(f"Error destroying login instance {name}: {e}")

        # 并发销毁所有登录实例
        if self._instances:
            tasks = [
                destroy_single(name, instance)
                for name, instance in list(self._instances.items())
            ]
            await asyncio.gather(*tasks)

        self._logins.clear()
        self._instances.clear()
        self._is_initialized = False

        logger.info("LoginRegister shutdown complete")

    async def _discover_logins(self) -> None:
        if not self._data_sources_dir.exists():
            logger.warning(f"Data sources directory not found: {self._data_sources_dir}")
            return

        dir_str = str(self._data_sources_dir.parent)
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)

        for login_file in self._data_sources_dir.rglob("login.py"):
            await self._load_logins_from_file(login_file)

    async def _load_logins_from_file(self, file_path: Path) -> None:
        try:
            rel_path = file_path.relative_to(self._data_sources_dir.parent)
            module_name = str(rel_path.with_suffix("")).replace(os.sep, ".")

            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    return
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BaseQRLogin)
                    and obj is not BaseQRLogin
                    and obj.__module__ == module_name
                ):
                    self._register_login_class(obj)

        except Exception as e:
            logger.error(f"Error loading logins from {file_path}: {e}")

    def _register_login_class(self, login_class: type[BaseQRLogin]) -> None:
        login_name = login_class.name or login_class.__name__

        if login_name in self._logins:
            logger.warning(f"Login {login_name} already registered, skipping")
            return

        self._logins[login_name] = login_class
        logger.info(f"Registered login class: {login_name}")

    def get_login_instance(self, login_name: str) -> BaseQRLogin:
        if login_name in self._instances:
            return self._instances[login_name]

        if login_name not in self._logins:
            raise LoginNotFoundError(f"Login '{login_name}' not found")

        login_class = self._logins[login_name]
        instance = login_class(browser_pool=self._browser_pool)
        self._instances[login_name] = instance

        return instance

    async def get_qrcode(self, login_name: str, qr_type: str = "default") -> QRCode:
        login = self.get_login_instance(login_name)
        return await login.get_qrcode(qr_type)

    async def get_qrcode_types(self, login_name: str) -> list[str]:
        login = self.get_login_instance(login_name)
        return await login.get_qrcode_types()

    def list_logins(self) -> list[str]:
        return list(self._logins.keys())

    async def list_login_info(self) -> list[dict[str, Any]]:
        """
        获取所有登录器信息，包含登录状态（并发优化版本）

        使用 asyncio.Semaphore 控制并发数，避免顺序等待导致的性能问题。
        """
        from omnidata.core.config import settings

        # 获取并发数配置
        concurrency = settings.login.check_concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def check_single_login(
            login_name: str, login_class: type[BaseQRLogin]
        ) -> dict[str, Any]:
            """检查单个登录器的状态"""
            async with semaphore:  # 限制并发数
                info = login_class.get_info()
                try:
                    instance = self.get_login_instance(login_name)
                    # 添加超时控制
                    status_info = await asyncio.wait_for(
                        instance.is_login(), timeout=settings.login.check_timeout
                    )
                    info["login_status"] = status_info.model_dump()
                except TimeoutError:
                    logger.warning(f"Timeout checking login status for {login_name}")
                    info["login_status"] = {"status": "error", "message": "检查超时"}
                except Exception as e:
                    logger.warning(f"Failed to get login status for {info.get('name')}: {e}")
                    info["login_status"] = {"status": "error", "message": str(e)}
                return info

        # 创建所有任务
        tasks = [
            check_single_login(login_name, login_class)
            for login_name, login_class in self._logins.items()
        ]

        # 并发执行所有任务
        login_infos = await asyncio.gather(*tasks)

        return login_infos

    async def get_login_info(self, login_name: str) -> dict[str, Any]:
        """
        获取登录器详情

        Args:
            login_name: 登录器名称

        Returns:
            登录器详细信息，包含登录状态
        """
        login = self.get_login_instance(login_name)
        info = login.get_info()

        # 获取支持的二维码类型
        qrcode_types = await login.get_qrcode_types()
        info["qrcode_types"] = qrcode_types

        # 获取登录状态
        try:
            status_info = await login.is_login()
            info["login_status"] = status_info.model_dump()
        except Exception as e:
            logger.warning(f"Failed to get login status for {login_name}: {e}")
            info["login_status"] = {"status": "error", "message": str(e)}

        return info

 

    @property
    def login_count(self) -> int:
        return len(self._logins)

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized


_login_register: LoginRegister | None = None
_register_lock: asyncio.Lock | None = None


async def get_login_register(browser_pool: BrowserPool | None = None) -> LoginRegister:
    global _login_register, _register_lock

    if _register_lock is None:
        _register_lock = asyncio.Lock()

    async with _register_lock:
        if _login_register is None:
            _login_register = LoginRegister(browser_pool)
            await _login_register.initialize()

        return _login_register


async def close_login_register() -> None:
    global _login_register

    if _login_register is not None:
        await _login_register.shutdown()
        _login_register = None


# 便捷访问器（用于非异步上下文）
def login_register() -> LoginRegister:
    """
    获取平台登录注册器（非异步版本）

    注意: 使用前需要确保已初始化

    Returns:
        LoginRegister: 登录注册器实例
    """
    global _login_register

    if _login_register is None:
        raise LoginRegistrationError(
            "Login register not initialized. Use await get_spider_register() first."
        )

    return _login_register
