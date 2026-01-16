"""
统一响应格式模块
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式"""

    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: T | None = Field(None, description="响应数据")


def success_response(data: Any, message: str = "操作成功") -> ApiResponse:
    """创建成功响应"""
    return ApiResponse(success=True, message=message, data=data)


def error_response(message: str, data: Any = None) -> ApiResponse:
    """创建错误响应"""
    return ApiResponse(success=False, message=message, data=data)


def paginated_success_response(
    items: list[Any], count: int, message: str = "获取成功"
) -> ApiResponse:
    """创建分页成功响应

    将 count 放入 data 中，前端统一处理
    """
    return ApiResponse(success=True, message=message, data={"items": items, "count": count})
