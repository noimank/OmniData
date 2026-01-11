"""
Bilibili 二维码登录模块
"""
import logging

from omnidata.core import BaseQRLogin, QRLoginState, QRCode

logger = logging.getLogger(__name__)


class EastmoneyQRLogin(BaseQRLogin):
    """Eastmoney 二维码登录"""

    name = "eastmoney"
    description = "东方财富 二维码登录"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    async def refresh_login_state(self) -> None:
        """
        重新保存登录状态到 Redis

        该方法会定期被调用以刷新登录状态。
        """
        context = await self.get_context_simple()
        page = await context.new_page()
        try:
            login_state = await self.is_login()
            if login_state.status == "success":
                await self.filter_file_load(page)
                await self.apply_anti_detection_scripts(page, "advanced")
                await page.goto("https://passport2.eastmoney.com/pub/basicinfo")
                await page.wait_for_load_state("domcontentloaded", timeout=2000)
                # 保存登录状态实现刷新
                await self.save_context_state(context, "eastmoney")
        except Exception as e:
            logger.error(f"Failed to refresh login state: {e}")
        finally:
            await page.close()
            await context.close()

    async def get_qrcode_types(self) -> list:
        return ["微信", "东方财富官方"]

    async def get_eastmoney_qr_code(self) -> QRCode:
        self._qr_context = await self.get_context_simple()
        self._qr_page = await self._qr_context.new_page()
        base_url = "https://passport2.eastmoney.com/pub/login"

        try:
            await self.filter_file_load(self._qr_page, "media")
            await self.apply_anti_detection_scripts(self._qr_page, "advanced")
            await self._qr_page.goto(base_url)
            await self._qr_page.wait_for_load_state("domcontentloaded", timeout=2000)
            # 点击同意
            await self._qr_page.locator("#frame_login").content_frame.locator("#mobile_login_content img").first.click()

            #  获取二维码图片URL
            qr_code_src = await self._qr_page.locator("#frame_login").content_frame.locator("#qrcode").get_attribute(
                "src")
            if qr_code_src.startswith("//"):
                qr_code_src = "https:" + qr_code_src

            return QRCode(url=qr_code_src, qr_type="东方财富官方", success=True, message="东方财富官方二维码成功")
        except Exception as e:
            logger.error(f"Failed to get Bilibili qrcode: {e}")
            # 出错就关闭，防止资源泄露
            await self.close()
            return QRCode(url="", qr_type="东方财富官方", success=False, message=f"东方财富官方二维码失败: {e}")

    async def get_weixin_qr_code(self) -> QRCode:
        self._qr_context = await self.get_context_simple()
        self._qr_page = await self._qr_context.new_page()
        base_url = "https://passport2.eastmoney.com/pub/login"
        try:
            await self.apply_anti_detection_scripts(self._qr_page, "advanced")
            await self.filter_file_load(self._qr_page, "media")
            await self._qr_page.goto(base_url)
            await self._qr_page.wait_for_load_state("domcontentloaded", timeout=2000)
            # 点击同意
            await self._qr_page.locator("#frame_login").content_frame.locator("#mobile_login_content img").first.click()
            # 点击微信登录按钮
            weixin_btn = self._qr_page.locator("#frame_login").content_frame.locator("#btn_wx")
            # 等待出现微信登录按钮
            await weixin_btn.wait_for(timeout=2000)
            await weixin_btn.click()
            # 等待页面加载完成
            weixin_qr_img = self._qr_page.locator(".js_normal_login.web_qrcode_img_area .web_qrcode_img_wrp")
            # 等待出现二维码
            await weixin_qr_img.wait_for(timeout=2000)
            qr_code_src = await weixin_qr_img.get_by_role('img').first.get_attribute('src')
            # 补齐完整的url
            if qr_code_src.startswith("/"):
                qr_code_src = "https://open.weixin.qq.com" + qr_code_src
            return QRCode(url=qr_code_src, qr_type="微信", success=True, message="获取微信二维码成功")

        except Exception as e:
            logger.error(f"Failed to get Weixin qrcode: {e}")
            # 出错就关闭，防止资源泄露
            await self.close()
            return QRCode(url="", qr_type="微信", success=False, message=f"获取微信二维码失败: {e}")

    async def get_qrcode(self, qr_type: str = "哔哩哔哩官方") -> QRCode:
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
                qr_code = await self.get_weixin_qr_code()
                return qr_code
            elif qr_type == "东方财富官方":
                qr_code = await self.get_eastmoney_qr_code()
                return qr_code

            else:
                return QRCode(success=False, message=f"不支持的二维码类型：{qr_type}， 可选值：{self.get_qrcode_types()}")

        except Exception as e:
            logger.error(f"Failed to get eastmoney qrcode: {e}")
            return QRCode(success=False, message=f"获取二维码失败: {e}")

    async def verify_login_state(self) -> QRLoginState:
        """
        验证二维码登录是否完成

        与 get_qrcode 共用 self._qr_page 和 self._qr_context

        Returns:
            包含登录状态的字典

        """
        if not self._qr_page:
            return QRLoginState(status="failed", message="QR code page not initialized, please call get_qrcode first")

        try:
            current_url = self._qr_page.url
            #登录完成后会跳转到：https://passport2.eastmoney.com/pub/BasicInfo
            if "BasicInfo" not in current_url:
                return QRLoginState(status="waiting", message="正在登录中..........")
            # 如何找不到会异常，不会执行以下代码，相反如果成功执行以下代码
            # 保存登录状态
            await self.save_context_state(self._qr_context, "eastmoney")
            await self.close()
            return QRLoginState(status="success", message="登录成功,且保存登录状态")

        except Exception as e:
            # logger.error(f"Failed to verify eastmoney login state: {e}")
            return QRLoginState(status="waiting", message="等待验证登录状态中.......")

    async def is_login(self) -> QRLoginState:
        """
        验证是否已登录

        使用独立的 page/context，与 get_qrcode 和 verify_login_state 分离

        Returns:
            是否已登录
        """
        context = await self.get_context_simple("eastmoney")
        page = await context.new_page()
        try:
            await self.apply_anti_detection_scripts(page, "advanced")
            await self.filter_file_load(page, "media")
            await page.goto("https://passport2.eastmoney.com/pub/BasicInfo")
            await page.wait_for_load_state("domcontentloaded", timeout=1500)

            # 已经跳转回登录界面了的话直接返回
            if "login" in page.url:
                return QRLoginState(status="not_logged_in", message="未登录东方财富")

            # 检查是否登录
            await page.locator("#pass_tab").wait_for(timeout=350)

            flag_text = await page.locator("#pass_tab").inner_text()

            for text in ["基本资料", "设置头像", "账户安全", "修改密码", "安全中心"]:
                if text in flag_text:
                    return QRLoginState(status="success", message="已登录东方财富")

            return QRLoginState(status="not_logged_in", message="未登录东方财富")

        except Exception as e:
            # logger.info(f"Failed to check eastmoney login status: {e}")
            return QRLoginState(status="not_logged_in", message=f"未登录东方财富")

        finally:
            await page.close()
            await context.close()
