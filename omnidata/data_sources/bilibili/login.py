"""
Bilibili 二维码登录模块
"""

import asyncio
import logging

from omnidata.core import BaseQRLogin, QRLoginState, QRCode

logger = logging.getLogger(__name__)


class BilibiliQRLogin(BaseQRLogin):
    """Bilibili 二维码登录"""

    name = "bilibili"
    description = "Bilibili 二维码登录"
    version = "1.0.0"
    author = "noimank"
    platform = "哔哩哔哩"

    async def refresh_login_state(self) -> None:
        """
        重新保存登录状态到 Redis

        该方法会定期被调用以刷新登录状态。
        """
        context = await self.browser_context_pool.get_context("bilibili")
        page = await context.new_page()
        try:
            login_state = await self.is_login()
            if login_state.status == "success":
                await self.filter_file_load(page, "media")
                await self.apply_anti_detection_scripts(page, "advanced")
                await page.goto("https://www.bilibili.com/")
                await page.wait_for_load_state("domcontentloaded", timeout=3000)
                # 保存登录状态实现刷新
                await self.save_context_state(context, "bilibili")
        finally:
            await page.close()

    async def get_qrcode_types(self) -> list:
        return ["微信", "哔哩哔哩官方"]

    async def get_bilibili_qr_code(self) -> QRCode:
        self._qr_context = await self.browser_context_pool.get_context("bilibili")
        self._qr_page = await self._qr_context.new_page()
        base_url = "https://www.bilibili.com/"

        try:
            await self.apply_anti_detection_scripts(self._qr_page, "advanced")
            await self.filter_file_load(self._qr_page, "media")
            await self._qr_page.goto(base_url)
            await self._qr_page.wait_for_load_state("domcontentloaded", timeout=2000)
            # 点击登录按钮
            await self._qr_page.locator(".header-login-entry").get_by_text("登录").click()

            qr_img = self._qr_page.locator(".login-scan-box img")
            # 等待出现二维码
            await qr_img.wait_for(timeout=2000)
            await asyncio.sleep(0.7)

            # 截取二维码图片并转换为 Base64（避免二次访问导致二维码刷新）
            qr_code_base64 = await self.screenshot_element_to_base64(
                self._qr_page, ".login-scan-box img"
            )

            return QRCode(
                url=qr_code_base64,
                qr_type="哔哩哔哩官方",
                success=True,
                message="获取哔哩哔哩官方二维码成功",
            )
        except Exception as e:
            logger.error(f"Failed to get Bilibili qrcode: {e}")
            # 出错就关闭，防止资源泄露
            await self.close()
            return QRCode(
                url="",
                qr_type="哔哩哔哩官方",
                success=False,
                message=f"获取哔哩哔哩官方二维码失败: {e}",
            )

    async def get_weixin_qr_code(self) -> QRCode:
        self._qr_context = await self.browser_context_pool.get_context("bilibili")
        self._qr_page = await self._qr_context.new_page()
        base_url = "https://www.bilibili.com/"
        try:
            await self.apply_anti_detection_scripts(self._qr_page, "advanced")
            await self.filter_file_load(self._qr_page, "media")
            await self._qr_page.goto(base_url)
            await self._qr_page.wait_for_load_state("domcontentloaded", timeout=2000)
            # 点击登录按钮
            await self._qr_page.locator(".header-login-entry").get_by_text("登录").click()
            # 点击微信登录按钮
            weixin_btn = self._qr_page.locator(".login-sns-content").get_by_text("微信登录")
            # 等待出现微信登录按钮
            await weixin_btn.wait_for(timeout=2000)
            await weixin_btn.click()
            # 等待页面加载完成

            weixin_qr_img = self._qr_page.locator(
                ".js_normal_login.web_qrcode_img_area .web_qrcode_img_wrp"
            )
            # 等待出现二维码
            await weixin_qr_img.wait_for(timeout=2000)
            qr_code_src = await weixin_qr_img.get_by_role("img").first.get_attribute("src")
            # 补齐完整的url
            if qr_code_src.startswith("/"):
                qr_code_src = "https://open.weixin.qq.com" + qr_code_src
            return QRCode(
                url=qr_code_src, qr_type="微信", success=True, message="获取微信二维码成功"
            )

        except Exception as e:
            logger.error(f"Failed to get Weixin qrcode: {e}")
            # 出错就关闭，防止资源泄露
            await self.close()
            return QRCode(url="", qr_type="微信", success=False, message=f"获取微信二维码失败: {e}")

    async def get_qrcode(self, qr_type: str = "哔哩哔哩官方") -> QRCode:
        """
        获取指定类型的二维码

        持有实例锁保护 _qr_page 生命周期，防止并发调用产生孤儿 page

        Args:
            qr_type: 二维码类型

        Returns:
            包含二维码信息的字典
        """
        async with self._lock:
            # 确保资源关闭，每次调用该函数都是新的操作
            await self.close()
            try:

                if qr_type == "微信":
                    qr_code = await self.get_weixin_qr_code()
                    return qr_code
                elif qr_type == "哔哩哔哩官方":
                    qr_code = await self.get_bilibili_qr_code()
                    return qr_code

                else:
                    return QRCode(
                        success=False,
                        message=f"不支持的二维码类型：{qr_type}， 可选值：{await self.get_qrcode_types()}",
                    )

            except Exception as e:
                logger.error(f"Failed to get Bilibili qrcode: {e}")
                return QRCode(success=False, message=f"获取二维码失败: {e}")

    async def verify_login_state(self) -> QRLoginState:
        """
        验证二维码登录是否完成

        与 get_qrcode 共用 self._qr_page 和 self._qr_context

        Returns:
            包含登录状态的字典

        """
        # 如果已经登录成功，直接返回成功状态（避免重复验证）
        if self._login_status.status == "success":
            return self._login_status

        async with self._lock:
            if not self._qr_page_alive():
                return QRLoginState(
                    status="failed",
                    message="QR code page not initialized, please call get_qrcode first",
                )

            try:

                flag_text = await self._qr_page.locator(".right-entry li").first.inner_text()
                if "登录" in flag_text:
                    return QRLoginState(status="waiting", message="正在登录中..........")
                # 如何找不到会异常，不会执行以下代码，相反如果成功执行以下代码

                # 保存登录状态
                await self.save_context_state(self._qr_context, "bilibili")
                await self.close()
                return QRLoginState(status="success", message="登录成功,且保存登录状态")

            except Exception:
                return QRLoginState(status="waiting", message=f"等待验证登录状态中......")

    async def is_login(self) -> QRLoginState:
        """
        验证是否已登录

        使用独立的 page/context，与 get_qrcode 和 verify_login_state 分离

        Returns:
            是否已登录
        """
        try:
            async with self.new_page("bilibili") as page:
                await self.filter_file_load(page, "media")
                await page.goto("https://account.bilibili.com/account/home")
                await page.wait_for_load_state("domcontentloaded", timeout=2000)
                # 已经跳转回登录界面了的话直接返回
                if "login" in page.url:
                    return QRLoginState(status="not_logged_in", message="未登录哔哩哔哩")

                # 检查是否登录
                await page.locator(".security-title").wait_for(timeout=500)
                flag_text = await page.locator(".security-left").first.inner_text()
                for text in [
                    "个人中心",
                    "账号安全",
                    "我的头像",
                    "我的硬币",
                    "我的记录",
                    "成就勋章",
                ]:
                    if text in flag_text:
                        return QRLoginState(status="success", message="已登录")

                return QRLoginState(status="not_logged_in", message="未登录")
        except Exception as e:
            logger.warning(f"Bilibili is_login check failed: {e}")
            return QRLoginState(status="not_logged_in", message="未登录哔哩哔哩")
