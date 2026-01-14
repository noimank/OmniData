"""
MCP 工具描述生成
"""

from typing import Any

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from pydantic.fields import FieldInfo


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
            enhanced_desc = _enhance_field_description(field_name, field_info)
            lines.append(f"    {field_name}: {enhanced_desc}")

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


def _extract_constraints(field_info: FieldInfo) -> list[str]:
    """
    从 FieldInfo 中提取约束信息

    Args:
        field_info: Pydantic 字段信息

    Returns:
        约束字符串列表，如 ["范围0~120", "最小长度1"]
    """
    constraints: dict[str, int] = {}
    suffixes: list[str] = []

    for metadata in field_info.metadata:
        type_name = type(metadata).__name__
        if type_name == "Ge":
            constraints["ge"] = metadata.ge
        elif type_name == "Le":
            constraints["le"] = metadata.le
        elif type_name == "Gt":
            constraints["gt"] = metadata.gt
        elif type_name == "Lt":
            constraints["lt"] = metadata.lt
        elif type_name == "MinLen":
            suffixes.append(f"最小长度{metadata.min_length}")
        elif type_name == "MaxLen":
            suffixes.append(f"最大长度{metadata.max_length}")

    # 组合数值范围为 "范围{min}~{max}"
    if "ge" in constraints and "le" in constraints:
        suffixes.append(f"范围{constraints['ge']}~{constraints['le']}")
    elif "ge" in constraints:
        suffixes.append(f"≥{constraints['ge']}")
    elif "le" in constraints:
        suffixes.append(f"≤{constraints['le']}")

    if "gt" in constraints and "lt" in constraints:
        suffixes.append(f"范围>{constraints['gt']}且<{constraints['lt']}")
    elif "gt" in constraints:
        suffixes.append(f">{constraints['gt']}")
    elif "lt" in constraints:
        suffixes.append(f"<{constraints['lt']}")

    return suffixes


def _enhance_field_description(field_name: str, field_info: FieldInfo) -> str:
    """
    增强字段描述，在原有描述后追加约束和默认值信息

    Args:
        field_name: 字段名称
        field_info: Pydantic 字段信息

    Returns:
        增强后的描述字符串
    """
    suffixes: list[str] = []

    # 1. 检查是否必需
    if field_info.is_required():
        suffixes.append("必填")

    # 2. 添加默认值（如果有）
    if field_info.default is not PydanticUndefined:
        if isinstance(field_info.default, str):
            default_repr = repr(field_info.default)  # 显示引号，如 "json"
        else:
            default_repr = str(field_info.default)
        suffixes.append(f"默认{default_repr}")

    # 3. 提取约束
    constraint_suffixes = _extract_constraints(field_info)
    suffixes.extend(constraint_suffixes)

    # 4. 追加到原描述
    base_desc = field_info.description or "无说明"
    if suffixes:
        return f"{base_desc}，" + "，".join(suffixes)
    return base_desc
