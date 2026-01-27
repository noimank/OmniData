"""
登录类注册器模块
"""

import asyncio
import datetime
import importlib
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any

from .base_qr_login import BaseQRLogin, QRCode
from .browser_context_pool import BrowserContextPool, get_browser_context_pool
from .exceptions import LoginNotFoundError, LoginRegistrationError

logger = logging.getLogger(__name__)


class LoginRegister:
    """登录类注册器"""

    def __init__(self, browser_context_pool: BrowserContextPool | None = None):
        self._data_sources_dir = Path(__file__).parent.parent.joinpath("data_sources")
        self._browser_context_pool = browser_context_pool
        self._logins: dict[str, type[BaseQRLogin]] = {}
        self._instances: dict[str, BaseQRLogin] = {}
        self._is_initialized = False
        # 统一后台刷新任务相关字段
        self._refresh_task: asyncio.Task | None = None
        self._running: bool = False
        self._stop_event: asyncio.Event | None = None
        self._num_seconds_per_hour: int = 3600  # 每小时秒数（固定）

        # 登录器到秒数的分配映射（在 initialize 时计算）
        self._login_second_assignments: dict[str, int] = {}

    async def initialize(self) -> None:
        if self._is_initialized:
            return

        if self._browser_context_pool is None:
            self._browser_context_pool = await get_browser_context_pool()

        await self._discover_logins()

        # 构建登录器到秒数的分配映射
        self._build_login_assignments()

        self._is_initialized = True

        # 注册完所有登录器后，统一启动后台刷新任务
        self._start_global_refresh_task()

        logger.info(f"LoginRegister initialized with {len(self._logins)} login classes")

    def _build_login_assignments(self) -> None:
        """
        构建登录器到秒数的分配映射

        使用哈希确保：
        - 同一登录器始终分配到同一秒
        - 均匀分布在 0-3599 秒范围内
        """
        self._login_second_assignments = {}
        for login_name in self._logins.keys():
            # 使用哈希将登录器名称映射到 0-3599 秒
            assigned_second = hash(login_name) % self._num_seconds_per_hour
            self._login_second_assignments[login_name] = assigned_second
            # logger.debug(f"Login '{login_name}' assigned to second {assigned_second}")

    def _start_global_refresh_task(self) -> None:
        """启动全局后台刷新任务（每秒轮询版本）"""
        if self._running:
            return

        self._running = True
        self._stop_event = asyncio.Event()

        async def refresh_loop():
            """每秒检查并刷新分配到当前秒数的登录器"""
            while self._running:
                try:
                    await asyncio.sleep(1)

                    if self._stop_event.is_set():
                        break

                    if not self._instances:
                        continue  # 没有活跃的登录器实例

                    # 获取当前时间在小时内的秒数（0-3599）
                    now = datetime.datetime.now()
                    current_second = now.minute * 60 + now.second

                    # 找出分配到当前秒的所有登录器
                    logins_to_refresh = []
                    for login_name, assigned_second in self._login_second_assignments.items():
                        if assigned_second == current_second and login_name in self._instances:
                            logins_to_refresh.append((login_name, self._instances[login_name]))

                    if not logins_to_refresh:
                        continue

                    logger.debug(
                        f"Second {current_second}: refreshing {len(logins_to_refresh)} login(s)"
                    )

                    # 并发刷新（但限制并发数）
                    # 使用现有配置中的 check_concurrency 作为并发限制
                    from omnidata.core.config import settings
                    concurrency = settings.login.check_concurrency

                    semaphore = asyncio.Semaphore(concurrency)

                    async def refresh_with_semaphore(login_name: str, instance: BaseQRLogin):
                        async with semaphore:
                            try:
                                await instance.refresh_login_state()
                                # 刷新成功后调用 is_login() 获取状态并缓存
                                try:
                                    from omnidata.core.config import settings
                                    status_info = await asyncio.wait_for(
                                        instance.is_login(), timeout=settings.login.check_timeout
                                    )
                                    instance.set_login_status(status_info)
                                except Exception as status_error:
                                    logger.warning(f"Failed to get login status after refresh for {login_name}: {status_error}")
                                await instance.close()
                                # logger.debug(f"Refreshed {login_name} at second {current_second}")
                            except Exception as e:
                                logger.error(f"Error refreshing {login_name}: {e}")

                    tasks = [
                        refresh_with_semaphore(name, instance)
                        for name, instance in logins_to_refresh
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)

                except Exception as e:
                    logger.error(f"Error in refresh loop: {e}")

        self._refresh_task = asyncio.create_task(refresh_loop())
        logger.info(
            f"Global login refresh task started (second-based polling, "
            f"{len(self._logins)} logins assigned across {self._num_seconds_per_hour} seconds)"
        )

    async def shutdown(self) -> None:
        """关闭所有登录实例，取消后台登录保持任务"""
        logger.info(f"Shutting down LoginRegister with {len(self._instances)} instances")

        # 1. 停止全局刷新任务
        self._running = False
        if self._stop_event:
            self._stop_event.set()

        if self._refresh_task and not self._refresh_task.done():
            try:
                await asyncio.wait_for(self._refresh_task, timeout=5.0)
            except (TimeoutError, asyncio.CancelledError):
                if not self._refresh_task.done():
                    self._refresh_task.cancel()
                    try:
                        await self._refresh_task
                    except asyncio.CancelledError:
                        pass

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
        instance = login_class(browser_context_pool=self._browser_context_pool)
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
        优先使用缓存状态，减少 is_login() 调用。
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
                instance = self.get_login_instance(login_name)
                info["login_status"] = instance.get_login_status().model_dump()
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
            status_info =  login.get_login_status()
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


def get_login_register() -> LoginRegister:
    """
    获取全局登录注册器实例（同步，无锁）

    Returns:
        LoginRegister: 登录注册器实例

    Raises:
        LoginRegistrationError: 未初始化
    """
    global _login_register
    if _login_register is None:
        raise LoginRegistrationError(
            "LoginRegister not initialized. "
            "Ensure main.py lifespan startup completes before calling this function."
        )
    return _login_register


def set_login_register(instance: LoginRegister) -> None:
    """
    设置全局登录注册器实例（由 main.py lifespan 调用）

    Args:
        instance: 登录注册器实例
    """
    global _login_register
    _login_register = instance


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
