"""
同花顺问财 二维码登录模块
"""

import asyncio
import base64
import logging

from omnidata.core import BaseQRLogin, QRLoginState, QRCode

logger = logging.getLogger(__name__)


class ThsIwencaiQRLogin(BaseQRLogin):
    """同花顺问财 二维码登录"""

    name = "ths_iwencai"
    description = "同花顺问财 二维码登录"
    version = "1.0.0"
    author = "noimank"
    platform = "同花顺问财"

    async def refresh_login_state(self) -> None:
        """
        重新保存登录状态到 Redis

        该方法会定期被调用以刷新登录状态。
        """
        context = await self.browser_context_pool.get_context("ths_iwencai")
        page = await context.new_page()
        try:
            login_state = await self.is_login()
            if login_state.status == "success":
                await self.filter_file_load(page, "media")
                await self.apply_anti_detection_scripts(page, "advanced")
                await page.goto("https://www.iwencai.com/unifiedwap/home/index")
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                # 保存登录状态实现刷新
                await self.save_context_state(context, "ths_iwencai")
        finally:
            await page.close()

    async def get_qrcode_types(self) -> list:
        """返回支持的二维码类型"""
        return ["微信", "同花顺APP"]

    async def get_qrcode(self, qr_type: str = "微信") -> QRCode:
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
                    qr_code = await self.get_weixin_qrcode()
                    return qr_code
                elif qr_type == "同花顺APP":
                    qr_code = await self.get_ths_qrcode()
                    return qr_code
                else:
                    return QRCode(
                        success=False,
                        message=f"不支持的二维码类型：{qr_type}， 可选值：{await self.get_qrcode_types()}",
                    )

            except Exception as e:
                logger.error(f"Failed to get ths_iwencai qrcode: {e}")
                return QRCode(success=False, message=f"获取二维码失败: {e}")

    async def get_weixin_qrcode(self) -> QRCode:
        """
        获取微信登录二维码

        Returns:
            包含二维码信息的字典
        """
        # 确保资源关闭，每次调用该函数都是新的操作
        await self.close()

        try:
            self._qr_context = await self.browser_context_pool.get_context("ths_iwencai")
            self._qr_page = await self._qr_context.new_page()
            base_url = "https://www.iwencai.com/unifiedwap/home/index"

            await self.apply_anti_detection_scripts(self._qr_page, "advanced")
            await self.filter_file_load(self._qr_page, "media")
            await self._qr_page.goto(base_url)
            await self._qr_page.wait_for_load_state("domcontentloaded")

            # 点击"注册 / 登录"按钮
            await self._qr_page.locator("text=注册 / 登录").hover()
            await asyncio.sleep(0.4)
            await self._qr_page.locator("text=注册 / 登录").click()

            # 等待登录弹窗容器可见
            await self._qr_page.locator(".login-window-wrap").wait_for(state="visible")

            # 等待 iframe 加载完成
            await self._qr_page.wait_for_selector("#login_iframe", state="visible")

            # 获取 iframe 句柄
            frame = self._qr_page.frame_locator("#login_iframe")

            # 定位微信登录按钮
            wechat_login_button = frame.locator('.btn_elem[l_type="weixin"]')
            await wechat_login_button.wait_for(state="visible")

            # 设置弹窗监听并点击微信登录
            async with self._qr_page.expect_popup() as popup_info:
                await wechat_login_button.click()

            # 处理微信登录弹窗
            popup_page = await popup_info.value
            await popup_page.wait_for_load_state("domcontentloaded")

            # 获取二维码图片URL
            qr_code_selector = ".js_qrcode_img.web_qrcode_img"
            await popup_page.wait_for_selector(qr_code_selector, state="visible")
            qr_code_url = await popup_page.locator(qr_code_selector).first.get_attribute("src")
            if qr_code_url.startswith("/"):
                qr_code_url = "https://open.weixin.qq.com" + qr_code_url

            logger.info(f"获取到微信登录二维码URL：{qr_code_url}")

            return QRCode(
                success=True, url=qr_code_url, qr_type="微信", message="获取微信二维码成功"
            )

        except Exception as e:
            logger.error(f"Failed to get WeChat qrcode: {e}")
            await self.close()
            return QRCode(url="", qr_type="微信", success=False, message=f"获取微信二维码失败: {e}")

    async def get_ths_qrcode(self) -> QRCode:
        """
        获取同花顺登录二维码

        Returns:
            包含二维码信息的字典
        """
        # 确保资源关闭，每次调用该函数都是新的操作
        await self.close()
        try:
            self._qr_context = await self.browser_context_pool.get_context("ths_iwencai")
            self._qr_page = await self._qr_context.new_page()
            base_url = "https://www.iwencai.com/unifiedwap/home/index"

            await self.apply_anti_detection_scripts(self._qr_page, "advanced")
            await self.filter_file_load(self._qr_page, "media")
            await self._qr_page.goto(base_url)
            await self._qr_page.wait_for_load_state("domcontentloaded")

            # 点击"注册 / 登录"按钮
            await self._qr_page.locator("text=注册 / 登录").hover()
            await asyncio.sleep(0.4)
            await self._qr_page.locator("text=注册 / 登录").click()

            # 等待登录弹窗容器可见
            await self._qr_page.locator(".login-window-wrap").wait_for(state="visible")

            # 等待 iframe 加载完成
            await self._qr_page.wait_for_selector("#login_iframe", state="visible")

            # 获取 iframe 句柄
            frame = self._qr_page.frame_locator("#login_iframe")

            # 定位二维码登录按钮
            qr_login_button = frame.locator("#to_qrcode_login")
            await qr_login_button.wait_for(state="visible")

            # 点击同花顺二维码登录
            await qr_login_button.click()
            await asyncio.sleep(2)

            # 获取二维码图片URL
            qr_code_selector = ".code-box img"
            await frame.locator(qr_code_selector).wait_for(state="visible")

            # 注意：frame_locator 返回的是 FrameLocator，需要先获取实际的 Frame
            # 但 screenshot_element_to_base64 需要 Page 对象，所以我们直接在这里截图
            element = frame.locator(qr_code_selector).first
            screenshot_bytes = await element.screenshot(type="png")
            image_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            qr_code_base64 = f"data:image/png;base64,{image_base64}"

            logger.info(f"获取到同花顺APP登录二维码（Base64格式）")

            return QRCode(
                success=True, url=qr_code_base64, qr_type="同花顺", message="获取同花顺二维码成功"
            )

        except Exception as e:
            logger.error(f"Failed to get THS qrcode: {e}")
            await self.close()
            return QRCode(
                url="", qr_type="同花顺", success=False, message=f"获取同花顺二维码失败: {e}"
            )

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

                await self._qr_page.wait_for_selector(
                    ".main-right-header", state="visible", timeout=1200
                )
                text = await self._qr_page.locator(".main-right-header").inner_text()
                if ("注册" in text) or ("登录" in text):
                    return QRLoginState(status="waiting", message="等待验证登录状态中...")

                # 没有登录的话会出错，无法执行以下语句
                # 保存登录状态
                await self.save_context_state(self._qr_context, "ths_iwencai")
                await self.close()
                return QRLoginState(status="success", message="登录成功，且保存登录状态")

            except Exception as e:
                logger.error(f"Error verifying login state: {e}")
                return QRLoginState(status="waiting", message="等待验证登录状态中...")

    async def is_login(self) -> QRLoginState:
        """
        验证是否已登录

        使用独立的 page/context，与 get_qrcode 和 verify_login_state 分离

        Returns:
            是否已登录
        """
        try:
            async with self.new_page("ths_iwencai") as page:
                await self.filter_file_load(page, "media")
                await page.goto("https://www.iwencai.com/unifiedwap/home/index")
                await page.wait_for_load_state("domcontentloaded", timeout=6000)

                # 检查是否登录 - 等待登录成功标志元素
                text = await page.locator(".main-right-header").inner_text()
                if ("注册" in text) or ("登录" in text):
                    return QRLoginState(status="not_logged_in", message="未登录同花顺问财")
                return QRLoginState(status="success", message="已登录同花顺问财")
        except Exception as e:
            logger.warning(f"Ths_iwencai is_login check failed: {e}")
            return QRLoginState(status="not_logged_in", message="未登录同花顺问财")
