"""
爬虫管理路由
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from omnidata.core import spider_register
from omnidata.core.exceptions import SpiderNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spiders", tags=["spiders"])


class SpiderRunRequest(BaseModel):
    """爬虫运行请求"""

    spider_name: str = Field(..., description="爬虫名称")
    params: dict[str, Any] = Field(default_factory=dict, description="爬虫参数")


class SpiderRunBatchRequest(BaseModel):
    """爬虫批量运行请求"""

    spider_name: str = Field(..., description="爬虫名称")
    params_list: list[dict[str, Any]] = Field(..., description="参数列表")
    max_concurrency: int = Field(default=3, ge=1, le=10, description="最大并发数")


@router.get("")
async def list_spiders():
    """
    列出所有已注册的爬虫

    Returns:
        爬虫信息列表
    """
    register = spider_register()
    spiders = register.list_spider_info()
    return {"count": len(spiders), "spiders": spiders}


@router.get("/{spider_name}")
async def get_spider_info(spider_name: str):
    """
    获取指定爬虫的详细信息

    Args:
        spider_name: 爬虫名称

    Returns:
        爬虫信息
    """
    try:
        register = spider_register()
        info = register.get_spider_info(spider_name)
        return info
    except SpiderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/run")
async def run_spider(request: SpiderRunRequest):
    """
    运行指定的爬虫

    Args:
        request: 运行请求，包含 spider_name 和 params

    Returns:
        爬虫执行结果
    """
    try:
        register = spider_register()
        result = await register.run_spider(request.spider_name, request.params)
        return result.to_dict()
    except SpiderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error running spider {request.spider_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-batch")
async def run_spider_batch(request: SpiderRunBatchRequest):
    """
    批量运行指定的爬虫

    Args:
        request: 批量运行请求，包含 spider_name、params_list 和 max_concurrency

    Returns:
        爬虫执行结果列表
    """
    try:
        register = spider_register()
        results = await register.run_spider_batch(
            request.spider_name,
            request.params_list,
            request.max_concurrency,
        )
        return {"count": len(results), "results": [r.to_dict() for r in results]}
    except SpiderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error running spider batch {request.spider_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SpiderValidateRequest(BaseModel):
    """爬虫参数验证请求"""

    params: dict[str, Any] = Field(default_factory=dict, description="待验证的参数")


@router.get("/{spider_name}/schema")
async def get_spider_schema(spider_name: str):
    """
    获取爬虫参数 schema（用于动态生成表单）

    Args:
        spider_name: 爬虫名称

    Returns:
        参数 schema 信息
    """
    try:
        register = spider_register()
        spider = register.get_spider_instance(spider_name)

        result = {
            "name": spider.name,
            "description": spider.description,
            "version": spider.version,
            "params_schema": {},
        }

        # 如果有参数模型，转换为 JSON Schema
        if spider.params_model is not None:
            schema = spider.params_model.model_json_schema()
            # 简化 schema，只保留必要信息
            result["params_schema"] = _simplify_schema(schema.get("properties", {}))
            result["required"] = schema.get("required", [])

        return result
    except SpiderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting spider schema {spider_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{spider_name}/validate")
async def validate_spider_params(spider_name: str, request: SpiderValidateRequest):
    """
    验证爬虫参数

    Args:
        spider_name: 爬虫名称
        request: 包含待验证参数的请求

    Returns:
        验证结果
    """
    try:
        register = spider_register()
        spider = register.get_spider_instance(spider_name)

        errors = []
        warnings = []

        # 如果有参数模型，进行验证
        if spider.params_model is not None:
            try:
                spider.params_model(**request.params)
            except Exception as e:
                errors.append(str(e))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    except SpiderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error validating spider params {spider_name}: {e}")
        return {"valid": False, "errors": [str(e)], "warnings": []}


def _simplify_schema(properties: dict) -> dict:
    """简化 JSON Schema，只保留必要信息"""
    result = {}
    for key, value in properties.items():
        result[key] = {
            "type": value.get("type", "string"),
            "title": value.get("title", key),
            "description": value.get("description", ""),
            "default": value.get("default"),
        }
        # 如果是枚举类型
        if "enum" in value:
            result[key]["enum"] = value["enum"]
    return result
