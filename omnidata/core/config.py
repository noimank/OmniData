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

    # 浏览器启动选项（反爬虫优化）
    args: list[str] = field(
        default_factory=lambda: [
            # 核心：禁用自动化控制特征
            "--disable-blink-features=AutomationControlled",
            # 移除 Navigator 相关检测特征
            "--exclude-switches=enable-automation",
            "--disable-infobars",
            # 禁用"Chrome正在受到自动化测试软件的控制"提示
            "--disable-extensions",
            # 禁用扩展以避免指纹差异
            "--no-first-run",
            "--no-default-browser-check",
            # 性能优化
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
            # 伪装浏览器指纹
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-component-extensions-with-background-pages",
            "--disable-features=TranslateUI,BlinkGenPropertyTrees",
            "--disable-ipc-flooding-protection",
            "--disable-renderer-backgrounding",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            "--force-color-profile=srgb",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--mute-audio",
            # 窗口大小（避免无头模式检测）
            "--window-size=1920,1080",
            # 语言设置
            "--lang=zh-CN",
            # 时区设置
            "--timezone=Asia/Shanghai",
            # 禁用密码保存提示
            "--disable-save-password-bubble",
            # 禁用默认检查
            "--disable-sync",
            # 忽略证书错误（谨慎使用）
            "--ignore-certificate-errors",
            # 禁用弹出窗口阻止
            "--disable-popup-blocking",
        ]
    )
    ignore_default_args: list[str] = field(
        default_factory=lambda: ["--enable-automation", "--enable-blink-features=IdleDetection"]
    )


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


@dataclass
class LoginConfig:
    """登录器配置"""

    check_concurrency: int = 5  # 登录状态检查的最大并发数
    check_timeout: int = 30  # 单次检查的超时时间（秒）


@dataclass
class DatabaseConfig:
    """数据库配置"""

    db_path: str = "data/omnidata.db"  # SQLite 数据库文件路径


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    app_name: str = "OmniData"
    app_version: str = "0.1.0"
    debug: bool = False

    # 模块配置
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    login: LoginConfig = field(default_factory=LoginConfig)
    db: DatabaseConfig = field(default_factory=DatabaseConfig)

    class Config:
        env_prefix = "OMNIDATA_"
        env_nested_delimiter = "__"


# 全局配置实例
settings = Settings()
