"""
OmniData API 客户端

提供同步和异步方法调用 OmniData 服务器接口
"""

from typing import Any

from pydantic import BaseModel, Field


class SpiderInfo(BaseModel):
    """爬虫信息"""

    name: str = Field(..., description="爬虫名称")
    description: str = Field(..., description="爬虫描述")
    version: str = Field(..., description="版本号")
    author: str = Field(..., description="作者")
    platform: str = Field(..., description="平台名称")
    params_schema: dict[str, Any] = Field(default_factory=dict, description="参数 Schema")
    required: list[str] = Field(default_factory=list, description="必填参数")


class SpiderResultData(BaseModel):
    """爬虫执行结果"""

    spider_name: str = Field(..., description="爬虫名称")
    success: bool = Field(..., description="是否成功")
    data: Any | None = Field(None, description="爬取的数据")
    message: str | None = Field(None, description="结果消息")
    started_at: str = Field(..., description="开始时间 ISO 格式")
    completed_at: str | None = Field(None, description="完成时间 ISO 格式")
    duration_seconds: float = Field(..., description="执行耗时（秒）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class SpiderSchemaData(BaseModel):
    """爬虫 Schema 信息"""

    name: str = Field(..., description="爬虫名称")
    description: str = Field(..., description="爬虫描述")
    version: str = Field(..., description="版本号")
    params_schema: dict[str, Any] = Field(default_factory=dict, description="参数 Schema")
    required: list[str] = Field(default_factory=list, description="必填参数")


class ValidateParamsResult(BaseModel):
    """参数验证结果"""

    valid: bool = Field(..., description="是否有效")
    errors: list[str] = Field(default_factory=list, description="错误列表")
    warnings: list[str] = Field(default_factory=list, description="警告列表")


class OmniDataApi:
    """OmniData API 客户端"""

    def __init__(self, base_url: str = "http://localhost:8380"):
        """
        初始化客户端

        Args:
            base_url: API 服务器地址
        """
        self.base_url = base_url.rstrip("/")
        self._async_client: "httpx.AsyncClient | None" = None  # type: ignore

    def _get_url(self, path: str) -> str:
        """构建完整 URL"""
        return f"{self.base_url}{path}"

    # ==================== 同步方法 ====================

    def list_spiders(self) -> dict[str, Any]:
        """
        列出所有爬虫（同步）

        Returns:
            {
                "success": bool,
                "message": str,
                "data": {"spiders": [...], "count": int}
            }
        """
        import httpx

        with httpx.Client(timeout=30.0) as client:
            response = client.get(self._get_url("/api/v1/spiders"))
            response.raise_for_status()
            return response.json()

    def get_spider_info(self, name: str) -> dict[str, Any]:
        """
        获取爬虫详情（同步）

        Args:
            name: 爬虫名称

        Returns:
            {
                "success": bool,
                "message": str,
                "data": SpiderInfo
            }
        """
        import httpx

        with httpx.Client(timeout=30.0) as client:
            response = client.get(self._get_url(f"/api/v1/spiders/{name}"))
            response.raise_for_status()
            return response.json()

    def run_spider(
        self, name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        运行爬虫（同步）

        Args:
            name: 爬虫名称
            params: 爬虫参数

        Returns:
            {
                "success": bool,
                "message": str,
                "data": SpiderResultData
            }
        """
        import httpx

        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                self._get_url("/api/v1/spiders/run"),
                json={"spider_name": name, "params": params or {}},
            )
            response.raise_for_status()
            return response.json()

    def run_spider_batch(
        self,
        name: str,
        params_list: list[dict[str, Any]],
        max_concurrency: int = 3,
    ) -> dict[str, Any]:
        """
        批量运行爬虫（同步）

        Args:
            name: 爬虫名称
            params_list: 参数列表
            max_concurrency: 最大并发数

        Returns:
            {
                "success": bool,
                "message": str,
                "data": {"count": int, "results": [... SpiderResultData ...]}
            }
        """
        import httpx

        with httpx.Client(timeout=600.0) as client:
            response = client.post(
                self._get_url("/api/v1/spiders/run-batch"),
                json={
                    "spider_name": name,
                    "params_list": params_list,
                    "max_concurrency": max_concurrency,
                },
            )
            response.raise_for_status()
            return response.json()

    def get_spider_schema(self, name: str) -> dict[str, Any]:
        """
        获取爬虫参数 Schema（同步）

        Args:
            name: 爬虫名称

        Returns:
            {
                "success": bool,
                "message": str,
                "data": SpiderSchemaData
            }
        """
        import httpx

        with httpx.Client(timeout=30.0) as client:
            response = client.get(self._get_url(f"/api/v1/spiders/{name}/schema"))
            response.raise_for_status()
            return response.json()

    def validate_spider_params(
        self, name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        验证爬虫参数（同步）

        Args:
            name: 爬虫名称
            params: 待验证的参数

        Returns:
            {
                "success": bool,
                "message": str,
                "data": ValidateParamsResult
            }
        """
        import httpx

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self._get_url(f"/api/v1/spiders/{name}/validate"),
                json={"params": params or {}},
            )
            response.raise_for_status()
            return response.json()

    # ==================== 异步方法 ====================

    async def _get_async_client(self) -> "httpx.AsyncClient":
        """获取异步客户端（单例）"""
        import httpx

        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(timeout=300.0)
        return self._async_client

    async def aclose(self):
        """关闭异步客户端"""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None

    async def async_list_spiders(self) -> dict[str, Any]:
        """
        列出所有爬虫（异步）

        Returns:
            {
                "success": bool,
                "message": str,
                "data": {"spiders": [...], "count": int}
            }
        """

        client = await self._get_async_client()
        response = await client.get(self._get_url("/api/v1/spiders"))
        response.raise_for_status()
        return response.json()

    async def async_get_spider_info(self, name: str) -> dict[str, Any]:
        """
        获取爬虫详情（异步）

        Args:
            name: 爬虫名称

        Returns:
            {
                "success": bool,
                "message": str,
                "data": SpiderInfo
            }
        """

        client = await self._get_async_client()
        response = await client.get(self._get_url(f"/api/v1/spiders/{name}"))
        response.raise_for_status()
        return response.json()

    async def async_run_spider(
        self, name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        运行爬虫（异步）

        Args:
            name: 爬虫名称
            params: 爬虫参数

        Returns:
            {
                "success": bool,
                "message": str,
                "data": SpiderResultData
            }
        """

        client = await self._get_async_client()
        response = await client.post(
            self._get_url("/api/v1/spiders/run"),
            json={"spider_name": name, "params": params or {}},
        )
        response.raise_for_status()
        return response.json()

    async def async_run_spider_batch(
        self,
        name: str,
        params_list: list[dict[str, Any]],
        max_concurrency: int = 3,
    ) -> dict[str, Any]:
        """
        批量运行爬虫（异步）

        Args:
            name: 爬虫名称
            params_list: 参数列表
            max_concurrency: 最大并发数

        Returns:
            {
                "success": bool,
                "message": str,
                "data": {"count": int, "results": [... SpiderResultData ...]}
            }
        """

        client = await self._get_async_client()
        response = await client.post(
            self._get_url("/api/v1/spiders/run-batch"),
            json={
                "spider_name": name,
                "params_list": params_list,
                "max_concurrency": max_concurrency,
            },
        )
        response.raise_for_status()
        return response.json()

    async def async_get_spider_schema(self, name: str) -> dict[str, Any]:
        """
        获取爬虫参数 Schema（异步）

        Args:
            name: 爬虫名称

        Returns:
            {
                "success": bool,
                "message": str,
                "data": SpiderSchemaData
            }
        """

        client = await self._get_async_client()
        response = await client.get(self._get_url(f"/api/v1/spiders/{name}/schema"))
        response.raise_for_status()
        return response.json()

    async def async_validate_spider_params(
        self, name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        验证爬虫参数（异步）

        Args:
            name: 爬虫名称
            params: 待验证的参数

        Returns:
            {
                "success": bool,
                "message": str,
                "data": ValidateParamsResult
            }
        """

        client = await self._get_async_client()
        response = await client.post(
            self._get_url(f"/api/v1/spiders/{name}/validate"),
            json={"params": params or {}},
        )
        response.raise_for_status()
        return response.json()

    # ==================== 便捷方法 ====================

    async def async_run(
        self, name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        运行爬虫的便捷方法（异步）

        Args:
            name: 爬虫名称
            params: 爬虫参数

        Returns:
            {
                "success": bool,
                "message": str,
                "data": SpiderResultData
            }
        """
        return await self.async_run_spider(name, params)

    def run(
        self, name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        运行爬虫的便捷方法（同步）

        Args:
            name: 爬虫名称
            params: 爬虫参数

        Returns:
            {
                "success": bool,
                "message": str,
                "data": SpiderResultData
            }
        """
        return self.run_spider(name, params)


