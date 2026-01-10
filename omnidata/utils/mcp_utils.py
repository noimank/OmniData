"""
MCP 工具描述生成
"""

from typing import Any

from pydantic import BaseModel


def generate_tool_description(spider: Any) -> str:
    """
    为 Spider 生成 Google-style docstring 格式的工具描述

    Args:
        spider: Spider 实例或类

    Returns:
        Google-style docstring 格式的描述字符串
    """
    # 获取基础描述
    base_desc = getattr(spider, "description", None) or f"运行 {spider.name} 爬虫"

    # 构建 docstring
    lines = [base_desc, ""]  # 摘要 + 空行

    # 如果有参数模型，添加 Args 部分
    params_model = getattr(spider, "params_model", None)
    if params_model:
        lines.append("Args:")
        for field_name, field_info in params_model.model_fields.items():
            desc = field_info.description or "无说明"
            lines.append(f"    {field_name}: {desc}")

    # 添加 Returns 部分
    lines.append("")
    lines.append("Returns:")
    lines.append("    爬取结果数据")

    return "\n".join(lines)


def extract_parameter_info(params_model: type[BaseModel]) -> list[dict[str, Any]]:
    """
    提取参数元数据信息

    Args:
        params_model: Pydantic 模型类

    Returns:
        参数信息列表
    """
    parameters = []

    for field_name, field_info in params_model.model_fields.items():
        param_info: dict[str, Any] = {
            "name": field_name,
            "type": _get_type_string(field_info.annotation),
            "required": field_info.is_required(),
            "description": field_info.description or "",
        }

        # 提取默认值（仅当是 JSON 可序列化的类型时）
        if field_info.default is not None and _is_json_serializable(field_info.default):
            param_info["default"] = field_info.default

        # 提取枚举值（如果有）
        if hasattr(field_info.annotation, "__metadata__"):
            for metadata in field_info.annotation.__metadata__:
                if hasattr(metadata, "enum"):
                    param_info["enum"] = [e.value for e in metadata.enum]

        parameters.append(param_info)

    return parameters


def _get_type_string(annotation: Any) -> str:
    """安全地将类型注解转换为字符串"""
    try:
        # 处理 typing 模块的类型
        if hasattr(annotation, "__name__"):
            return annotation.__name__
        if hasattr(annotation, "__origin__"):
            origin = annotation.__origin__
            origin_name = getattr(origin, "__name__", str(origin))
            args = annotation.__args__ if hasattr(annotation, "__args__") else ()
            if args:
                args_str = ", ".join(_get_type_string(arg) for arg in args)
                return f"{origin_name}[{args_str}]"
            return origin_name
        return str(annotation)
    except Exception:
        return "unknown"


def _is_json_serializable(value: Any) -> bool:
    """检查值是否可以 JSON 序列化"""
    if value is None:
        return True
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_json_serializable(item) for item in value)
    if isinstance(value, dict):
        return all(_is_json_serializable(k) and _is_json_serializable(v) for k, v in value.items())
    return False
