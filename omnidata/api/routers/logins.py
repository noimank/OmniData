"""
登录管理路由
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from omnidata.api.responses import success_response, error_response
from omnidata.core import get_login_register
from omnidata.core.exceptions import LoginNotFoundError, LoginRegistrationError
from omnidata.utils import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/logins", tags=["logins"])


class QrcodeRequest(BaseModel):
    """二维码请求"""

    qr_type: str = Field(default="default", description="二维码类型")


@router.get("")
async def list_logins():
    """
    列出所有登录器（包含登录状态）

    Returns:
        登录器列表，每个登录器包含 login_status 字段
    """
    try:
        register = get_login_register()
        logins = await register.list_login_info()
        return success_response({"logins": logins, "count": len(logins)}, "获取登录器列表成功")
    except LoginRegistrationError as e:
        logger.error(f"Error listing logins: {e}")
        return error_response(f"获取登录器列表失败: {str(e)}")


@router.get("/{login_name}")
async def get_login_detail(login_name: str):
    """
    获取登录器详情（包含登录状态）

    Args:
        login_name: 登录器名称

    Returns:
        登录器详细信息，包含 login_status 字段
    """
    try:
        register = get_login_register()
        login = await register.get_login_info(login_name)
        return success_response(login, "获取登录器详情成功")
    except LoginNotFoundError as e:
        return error_response(f"登录器不存在: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting login detail: {e}")
        return error_response(f"获取登录器详情失败: {str(e)}")


@router.post("/{login_name}/qrcode")
async def get_qrcode(login_name: str, request: QrcodeRequest):
    """
    获取登录二维码

    Args:
        login_name: 登录器名称
        request: 二维码请求，包含 qr_type

    Returns:
        二维码信息
    """
    try:
        register = get_login_register()
        qrcode = await register.get_qrcode(login_name, request.qr_type)

        return success_response(
            {"login_name": login_name, "url": qrcode.url, "qr_type": request.qr_type},
            f"获取 {request.qr_type} 二维码成功",
        )
    except LoginNotFoundError as e:
        return error_response(f"登录器不存在: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting qrcode: {e}")
        return error_response(f"获取二维码失败: {str(e)}")


@router.post("/{login_name}/verify")
async def verify_login(login_name: str):
    """
    验证登录状态（轮询接口）

    Args:
        login_name: 登录器名称

    Returns:
        登录状态
    """
    try:
        register = get_login_register()
        login = register.get_login_instance(login_name)
        status_info = await login.verify_login_state()
        return success_response(status_info.model_dump(), "验证登录状态成功")

    except LoginNotFoundError as e:
        return error_response(f"登录器不存在: {str(e)}")
    except Exception as e:
        logger.error(f"Error verifying login: {e}")
        return error_response(f"验证登录状态失败: {str(e)}")


@router.get("/{login_name}/status")
async def get_login_status(login_name: str):
    """
    检查当前登录状态

    Args:
        login_name: 登录器名称

    Returns:
        登录状态
    """
    try:
        register = get_login_register()
        login = register.get_login_instance(login_name)

        # 调用登录器的 is_login 方法实际验证登录状态
        status_info = await login.is_login()
        # 更新缓存
        login.set_login_status(status_info)
        return success_response(status_info.model_dump(), "获取登录状态成功")

    except LoginNotFoundError as e:
        return error_response(f"登录器不存在: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting login status: {e}")
        return error_response(f"获取登录状态失败: {str(e)}")


@router.delete("/{login_name}/session")
async def clear_login_session(login_name: str):
    """
    清除登录状态

    Args:
        login_name: 登录器名称

    Returns:
        操作结果
    """
    try:
        # 清除 Redis 中的 context state
        redis = await get_redis()
        key = f"omnidata:context_state:{login_name}"
        await redis.delete(key)

        return success_response({"login_name": login_name}, "登录状态已清除")

    except Exception as e:
        logger.error(f"Error clearing login session: {e}")
        return error_response(f"清除登录状态失败: {str(e)}")


@router.post("/{login_name}/cleanup")
async def cleanup_qrcode_resources(login_name: str):
    """
    清理二维码页面资源

    当用户取消登录或二维码过期时，清理 BaseQRLogin 实例中的
    _qr_page 和 _qr_context，避免资源泄露。

    Args:
        login_name: 登录器名称

    Returns:
        操作结果
    """
    try:
        register = get_login_register()
        login = register.get_login_instance(login_name)

        # 调用 close 方法清理资源
        await login.close()

        logger.info(f"Successfully cleaned up QR code resources for {login_name}")
        return success_response({"login_name": login_name}, "二维码资源已清理")
    except LoginNotFoundError as e:
        return error_response(f"登录器不存在: {str(e)}")
    except Exception as e:
        logger.error(f"Error cleaning up QR code resources for {login_name}: {e}")
        return error_response(f"清理二维码资源失败: {str(e)}")
