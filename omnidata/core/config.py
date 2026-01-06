"""
配置模块
"""

from dataclasses import dataclass, field

from pydantic_settings import BaseSettings


@dataclass
class BrowserConfig:
    """浏览器配置"""

    headless: bool = True
    pool_initial_size: int = 2  # 初始化时创建的浏览器数量
    idle_timeout: int = 300  # 空闲超时时间(秒)
    launch_timeout: int = 30  # 启动超时时间(秒)

    # 浏览器启动选项
    args: list[str] = field(
        default_factory=lambda: [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ]
    )
    ignore_default_args: list[str] = field(default_factory=list)


@dataclass
class RedisConfig:
    """Redis 配置"""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    max_connections: int = 10
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    decode_responses: bool = True
    context_state_ttl: int = 604800  # context 状态过期时间(秒)，默认7天


@dataclass
class AuthConfig:
    """认证配置"""

    api_key: str | None = None  # API KEY，可选配置


@dataclass
class LoginConfig:
    """登录器配置"""

    check_concurrency: int = 5  # 登录状态检查的最大并发数
    check_timeout: int = 30  # 单次检查的超时时间（秒）


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    app_name: str = "OmniData"
    app_version: str = "0.1.0"
    debug: bool = False

    # 模块配置
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    login: LoginConfig = field(default_factory=LoginConfig)

    class Config:
        env_prefix = "OMNIDATA_"
        env_nested_delimiter = "__"


# 全局配置实例
settings = Settings()
