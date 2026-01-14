"""
同花顺10jqka 二维码登录模块
"""
import logging

from omnidata.core import BaseQRLogin, QRLoginState, QRCode

logger = logging.getLogger(__name__)


class ThsTenJQKaQRLogin(BaseQRLogin):
    """同花顺10jqka 二维码登录"""

    name = "ths_10jqka"
    description = "同花顺10jqka 二维码登录"
    version = "1.0.0"
    author = "noimank"
    platform = "同花顺10jqka"

    async def refresh_login_state(self) -> None:
        """
        重新保存登录状态到 Redis

        该方法会定期被调用以刷新登录状态。
        """
        context = await self.get_context_simple("ths_10jqka")
        page = await context.new_page()
        try:
            login_state = await self.is_login()
            if login_state.status == "success":
                await self.filter_file_load(page, "media")
                await self.apply_anti_detection_scripts(page, "advanced")
                await page.goto("https://upass.10jqka.com.cn/bind/")
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                # 保存登录状态实现刷新
                await self.save_context_state(context, "ths_10jqka")
        except Exception as e:
            logger.error(f"Failed to refresh login state: {e}")
        finally:
            await page.close()
            await context.close()

    async def get_qrcode_types(self) -> list:
        """返回支持的二维码类型"""
        return ["微信", "同花顺APP"]

    async def get_qrcode(self, qr_type: str = "微信") -> QRCode:
        """
        获取指定类型的二维码

        Args:
            qr_type: 二维码类型

        Returns:
            包含二维码信息的字典
        """

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
                return QRCode(success=False, message=f"不支持的二维码类型：{qr_type}， 可选值：{self.get_qrcode_types()}")

        except Exception as e:
            logger.error(f"Failed to get eastmoney qrcode: {e}")
            return QRCode(success=False, message=f"获取二维码失败: {e}")

    async def get_weixin_qrcode(self, qr_type: str = "微信") -> QRCode:
        """
        获取指定类型的二维码

        Args:
            qr_type: 二维码类型

        Returns:
            包含二维码信息的字典
        """
        # 确保资源关闭，每次调用该函数都是新的操作
        await self.close()

        if qr_type != "微信":
            return QRCode(
                success=False,
                message=f"不支持的二维码类型：{qr_type}，可选值：微信"
            )

        try:
            self._qr_context = await self.get_context_simple("ths_10jqka")
            self._qr_page = await self._qr_context.new_page()
            base_url = "https://upass.10jqka.com.cn/login"

            await self.apply_anti_detection_scripts(self._qr_page, "advanced")
            await self.filter_file_load(self._qr_page, "media")
            await self._qr_page.goto(base_url)
            await self._qr_page.wait_for_load_state("domcontentloaded", timeout=5000)

            # 等待弹窗出现并获取二维码图片
            # 微信登录弹窗会出现在页面中，需要等待二维码加载完成
            await self._qr_page.wait_for_timeout(2000)

            # 查找二维码图片 - 微信登录弹窗中的二维码
            # 等待弹窗
            async with self._qr_page.expect_popup() as popup_info:
                # 点击微信登录按钮
                weixin_btn = self._qr_page.locator('a.btn_elem[l_type="weixin"]')
                await weixin_btn.wait_for(timeout=3000)
                await weixin_btn.click()

            # 在弹窗中查找二维码
            popup = await popup_info.value
            await popup.wait_for_load_state("domcontentloaded")  # 等待新窗口加载完成

            weixin_qr_img = popup.locator(".js_normal_login.web_qrcode_img_area .web_qrcode_img_wrp")
            # 等待出现二维码
            await weixin_qr_img.wait_for(timeout=2000)
            qr_code_src = await weixin_qr_img.get_by_role('img').first.get_attribute('src')
            # 补齐完整的url
            if qr_code_src.startswith("/"):
                qr_code_src = "https://open.weixin.qq.com" + qr_code_src


            return QRCode(
                success=True,
                url=qr_code_src,
                qr_type="微信",
                message="获取微信二维码成功"
            )

        except Exception as e:
            logger.error(f"Failed to get WeChat qrcode: {e}")
            await self.close()
            return QRCode(
                url="",
                qr_type="微信",
                success=False,
                message=f"获取微信二维码失败: {e}"
            )
    async def get_ths_qrcode(self) -> QRCode:
        """
        获取指定类型的二维码


        Returns:
            包含二维码信息的字典
        """
        # 确保资源关闭，每次调用该函数都是新的操作
        await self.close()

        try:
            self._qr_context = await self.get_context_simple("ths_10jqka")
            self._qr_page = await self._qr_context.new_page()
            base_url = "https://upass.10jqka.com.cn/login"

            await self.apply_anti_detection_scripts(self._qr_page, "advanced")
            await self.filter_file_load(self._qr_page, "media")
            await self._qr_page.goto(base_url)
            await self._qr_page.wait_for_load_state("domcontentloaded", timeout=5000)

            #点击二维码
            await self._qr_page.locator("#to_qrcode_login").click()

            #给时间等待加载二维码
            await self._qr_page.wait_for_timeout(1100)
            code_box_img = self._qr_page.locator(".code-box img")
            await code_box_img.wait_for(state="visible")

            qr_code_src = await code_box_img.first.get_attribute('src')
            # 补齐完整的url
            if qr_code_src.startswith("/"):
                qr_code_src = "https://upass.10jqka.com.cn/" + qr_code_src

            return QRCode(
                success=True,
                url=qr_code_src,
                qr_type="同花顺APP",
                message="获取同花顺APP二维码成功"
            )

        except Exception as e:
            logger.error(f"Failed to get WeChat qrcode: {e}")
            await self.close()
            return QRCode(
                url="",
                qr_type="同花顺APP",
                success=False,
                message=f"获取同花顺APP二维码失败: {e}"
            )

    async def verify_login_state(self) -> QRLoginState:
        """
        验证二维码登录是否完成

        与 get_qrcode 共用 self._qr_page 和 self._qr_context

        Returns:
            包含登录状态的字典
        """
        if not self._qr_page:
            return QRLoginState(
                status="failed",
                message="QR code page not initialized, please call get_qrcode first"
            )

        try:
            # 检查是否登录成功 - 通过url变化判断
            await self._qr_page.wait_for_timeout(500)
            current_url = self._qr_page.url
            if "open.weixin.qq" in current_url:
                return QRLoginState(status="waiting", message=f"等待验证登录状态中...")

            # 如果页面不再是登录页面，说明登录成功
            if 'login' not in current_url and "10jqka.com" in current_url:
                # 保存登录状态
                await self.save_context_state(self._qr_context, "ths_10jqka")
                await self.close()
                return QRLoginState(
                    status="success",
                    message="登录成功，且保存登录状态"
                )
            else:
                return QRLoginState(status="waiting", message=f"等待验证登录状态中...")


        except Exception as e:
            logger.error(f"Error verifying login state: {e}")
            return QRLoginState(status="waiting", message=f"等待验证登录状态中...")

    async def is_login(self) -> QRLoginState:
        """
        验证是否已登录

        使用独立的 page/context，与 get_qrcode 和 verify_login_state 分离

        Returns:
            是否已登录
        """
        context = await self.get_context_simple("ths_10jqka")
        page = await context.new_page()
        try:
            await self.apply_anti_detection_scripts(page, "advanced")
            await self.filter_file_load(page, "media")
            #去修改密码页面，每登录就是会跳回登录界面
            await page.goto("https://upass.10jqka.com.cn/bind/")

            await page.wait_for_load_state("domcontentloaded", timeout=3000)

            # 已经跳转回登录界面了的话直接返回
            if 'login' in page.url:
                return QRLoginState(status="not_logged_in", message="未登录同花顺10jqka")

            return QRLoginState(status="success", message="已登录同花顺10jqka网站")

        except Exception as e:
            logger.error(f"Failed to check 10jqka login status: {e}")
            return QRLoginState(status="not_logged_in", message=f"未登录同花顺10jqka")

        finally:
            await page.close()
            await context.close()
