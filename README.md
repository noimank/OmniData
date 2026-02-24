# OmniData

一个基于 Playwright 和 FastAPI 的可扩展网页爬虫框架，提供浏览器池管理、自动注册和高度可扩展的架构。

## ?? 文档

**完整文档：[https://noimank.github.io/OmniData](https://noimank.github.io/OmniData)**

### 本地构建文档

```bash
# 安装文档依赖
uv sync --group dev

# 启动本地文档服务器
uv run mkdocs serve

# 访问 http://localhost:8000
```

## 技术栈

- **FastAPI** 0.128.0 - Web 框架
- **APScheduler** 3.11.2 - 任务调度
- **FastMCP** 2.14.1 - MCP 协议支持
- **Redis** 6.2.0 - 缓存
- **Playwright** 1.57.0 - 浏览器自动化

## 项目结构

```
omnidata/
├── omnidata/              # 主包目录
│   ├── core/              # 核心模块
│   │   ├── base_web_spider.py    # 爬虫基类
│   │   ├── browser_pool.py       # 浏览器池
│   │   ├── spider_register.py    # 爬虫注册器
│   │   ├── config.py             # 配置管理
│   │   └── exceptions.py         # 自定义异常
│   ├── data_sources/      # 数据源目录（爬虫实现）
│   ├── utils/             # 工具模块
│   └── api/               # API 接口
├── main.py                # 主入口
├── pyproject.toml         # 项目配置
└── .env.example           # 环境变量示例
```

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv 安装依赖
uv sync

# 安装 Playwright 浏览器
uv run playwright install chromium
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置 Redis 连接信息
```

### 3. 启动服务

```bash
# 启动 API 服务
uv run python main.py

# 或使用 uvicorn 直接启动
uv run uvicorn omnidata.api.main:app --reload
```

## 创建爬虫

在 `omnidata/data_sources/` 目录下创建新的爬虫文件：

```python
# omnidata/data_sources/my_spider.py
from pydantic import BaseModel, Field
from omnidata.core.base_web_spider import BaseWebSpider

class MyParams(BaseModel):
    url: str = Field(..., description="目标URL")
    screenshot: bool = Field(default=False, description="是否截图")

class MySpider(BaseWebSpider):
    name = "my_spider"
    description = "我的爬虫"
    version = "1.0.0"
    enabled = True

    # 定义参数模型
    params_model = MyParams

    async def crawl(self, params: MyParams) -> dict:
        """爬虫核心逻辑"""
        # 通过 self.get_page_context() 获取页面（推荐）
        async with self.get_page_context() as page:
            await page.goto(params.url)

            result = {
                "title": await page.title(),
                "url": page.url
            }

            if params.screenshot:
                import base64
                screenshot_bytes = await page.screenshot()
                result["screenshot"] = base64.b64encode(screenshot_bytes).decode("utf-8")

            return result
```

爬虫会被自动注册，无需手动配置！

### 可用属性和方法

在 `crawl` 方法中可以使用：

**属性：**
- `self.config` - 爬虫配置对象
- `self.browser_pool` - 浏览器池实例

**方法：**
- `async with self.get_page_context()` - 获取页面（自动管理，推荐）
- `page = await self.get_page()` - 获取页面（需手动关闭）
- `context = await self.get_context()` - 获取浏览器上下文

**参数：**
- `params` - 验证后的参数对象（Pydantic 模型），通过方法参数传入

## 使用 API

### 列出所有爬虫

```bash
curl http://localhost:8380/spiders
```

### 获取爬虫详情

```bash
curl http://localhost:8380/spiders/example_spider
```

### 运行单个爬虫

```bash
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "example_spider",
    "params": {
      "url": "https://example.com",
      "screenshot": true
    }
  }'
```

### 批量运行爬虫

```bash
curl -X POST http://localhost:8380/spiders/run-batch \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "example_spider",
    "params_list": [
      {"url": "https://example.com"},
      {"url": "https://example.org"}
    ],
    "max_concurrency": 3
  }'
```

## 核心功能

### BaseWebSpider 基类

提供完整的爬虫生命周期管理：

- **参数验证**：基于 Pydantic 的自动参数验证
- **预处理**：`preprocess()` 钩子方法
- **执行**：`crawl()` 核心逻辑（需子类实现）
- **后处理**：`postprocess()` 结果处理
- **重试机制**：自动重试失败的请求

### BrowserPool 浏览器池

- 支持多浏览器实例管理
- 自动清理空闲浏览器
- 上下文复用
- 连接池统计

### SpiderRegister 自动注册

- 自动发现 `data_sources/` 下的所有爬虫
- 统一管理爬虫实例
- 支持批量执行

## 配置

主要配置项（通过环境变量设置）：

```bash
# 浏览器配置
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__POOL_INITIAL_SIZE=2

# 爬虫配置
OMNIDATA_SPIDER__RETRY_TIMES=3
OMNIDATA_SPIDER__RETRY_DELAY=1

# Redis 配置
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379
```

## 许可证

MIT License
