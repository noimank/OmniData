"""
反爬虫检测脚本模块

提供多种反检测脚本，用于隐藏 Playwright 自动化特征
"""

import logging
from abc import ABC, abstractmethod

from playwright.async_api import Page
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)


class AntiDetectionScript(ABC):
    """反检测脚本基类"""

    name: str = ""

    @abstractmethod
    async def apply(self, page: Page) -> None:
        """
        应用反检测脚本到 page

        Args:
            page: Playwright Page 实例
        """
        pass


class NavigatorWebdriverScript(AntiDetectionScript):
    """
    修改 navigator.webdriver 属性

    将 navigator.webdriver 设置为 false，这是最基本的反检测措施
    """

    name = "navigator_webdriver"

    async def apply(self, page: Page) -> None:
        """修改 navigator.webdriver 为 false"""
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
        """
        )
        logger.debug("Applied navigator.webdriver script")


class ChromeRuntimeScript(AntiDetectionScript):
    """
    修改 Chrome runtime 相关属性

    修改 window.chrome 相关属性，使其看起来像真实的 Chrome 浏览器
    """

    name = "chrome_runtime"

    async def apply(self, page: Page) -> None:
        """添加 window.chrome 对象"""
        await page.add_init_script(
            """
            window.chrome = {
                runtime: {}
            };
        """
        )
        logger.debug("Applied chrome.runtime script")


class PermissionsQueryScript(AntiDetectionScript):
    """
    修改 permissions API

    修改 navigator.permissions.query，防止被检测为自动化
    """

    name = "permissions_query"

    async def apply(self, page: Page) -> None:
        """修改 permissions.query"""
        await page.add_init_script(
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """
        )
        logger.debug("Applied permissions.query script")


class NavigatorLanguagesScript(AntiDetectionScript):
    """
    修改 navigator.languages

    设置合理的语言值
    """

    name = "navigator_languages"

    async def apply(self, page: Page) -> None:
        """修改 navigator.languages"""
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en']
            });
        """
        )
        logger.debug("Applied navigator.languages script")


class PlaywrightStealthScript(AntiDetectionScript):
    """
    使用 playwright-stealth 库

    这是最全面的反检测方案，会应用多种反检测技术
    """

    name = "playwright_stealth"

    async def apply(self, page: Page) -> None:
        """应用 playwright-stealth（page 级，避免在共享 context 上累积 init script）"""
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        logger.debug("Applied playwright-stealth script")


class WebDriverDataScript(AntiDetectionScript):
    """
    修改 navigator.webdriver 相关的额外数据

    修改更多可能暴露自动化特征的属性
    """

    name = "webdriver_data"

    async def apply(self, page: Page) -> None:
        """修改 webdriver 相关数据"""
        await page.add_init_script(
            """
            // 覆盖 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 覆盖 chrome 对象
            window.chrome = {
                app: {
                    isInstalled: false,
                },
                runtime: {},
            };

            // 覆盖 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """
        )
        logger.debug("Applied webdriver_data script")


# 脚本无状态，使用模块级单例（每次建页不再重复实例化）
ALL_SCRIPTS: dict[str, AntiDetectionScript] = {
    NavigatorWebdriverScript.name: NavigatorWebdriverScript(),
    ChromeRuntimeScript.name: ChromeRuntimeScript(),
    PermissionsQueryScript.name: PermissionsQueryScript(),
    NavigatorLanguagesScript.name: NavigatorLanguagesScript(),
    WebDriverDataScript.name: WebDriverDataScript(),
    PlaywrightStealthScript.name: PlaywrightStealthScript(),
}

# 预定义的脚本组合
SCRIPT_PRESETS: dict[str, list[AntiDetectionScript]] = {
    "basic": [
        ALL_SCRIPTS[NavigatorWebdriverScript.name],
        ALL_SCRIPTS[ChromeRuntimeScript.name],
    ],
    "standard": [
        ALL_SCRIPTS[NavigatorWebdriverScript.name],
        ALL_SCRIPTS[ChromeRuntimeScript.name],
        ALL_SCRIPTS[PermissionsQueryScript.name],
        ALL_SCRIPTS[NavigatorLanguagesScript.name],
    ],
    "advanced": [
        ALL_SCRIPTS[NavigatorWebdriverScript.name],
        ALL_SCRIPTS[ChromeRuntimeScript.name],
        ALL_SCRIPTS[PermissionsQueryScript.name],
        ALL_SCRIPTS[NavigatorLanguagesScript.name],
        ALL_SCRIPTS[WebDriverDataScript.name],
    ],
}


def get_anti_scripts_by_names(names: str | list[str]) -> list[AntiDetectionScript]:
    """
    根据名称获取反检测脚本（返回模块级单例）

    Args:
        names: 脚本名称或名称列表，支持预设名称(basic/standard/advanced)或单个脚本名称

    Returns:
        反检测脚本实例列表

    Examples:
        # 使用预设
        scripts = get_anti_scripts_by_names("basic")
        scripts = get_anti_scripts_by_names("advanced")

        # 使用单个脚本
        scripts = get_anti_scripts_by_names("navigator_webdriver")

        # 使用多个脚本
        scripts = get_anti_scripts_by_names(["navigator_webdriver", "chrome_runtime"])
    """
    if isinstance(names, str):
        names = [names]

    scripts: list[AntiDetectionScript] = []

    for name in names:
        # 检查是否为预设组合
        if name in SCRIPT_PRESETS:
            scripts.extend(SCRIPT_PRESETS[name])
        # 检查是否为单个脚本
        elif name in ALL_SCRIPTS:
            scripts.append(ALL_SCRIPTS[name])
        else:
            logger.warning(f"Unknown anti-detection script: {name}")

    return scripts
