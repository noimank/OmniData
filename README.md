# OmniData

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-green.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-1.57+-blue.svg)](https://playwright.dev/)

OmniData 是一个企业级的可扩展网页爬虫框架，基于 Playwright 和 FastAPI 构建，提供强大的浏览器自动化能力、智能登录态管理以及 MCP 协议集成支持。

**作者**: noimank (noimank@163.com)

---

## 特性

### 核心功能
- **浏览器自动化**: 基于 Playwright 实现完整的浏览器自动化能力，支持.headers、Cookie、LocalStorage 等全流程控制
- **LRU 单例模式**: 核心组件使用 LRU 缓存实现线程安全单例，优化资源管理
- **Context 池化**: 单 Browser 多 Context 架构，Context 自动复用与回收，显著降低内存占用
- **自动注册机制**: 扫描 `data_sources/` 目录自动发现爬虫和登录器，零配置启动
- **Redis 状态持久化**: cookies 和 localStorage 自动持久化到 Redis，支持登录态长期保持

### 智能登录管理
- **二维码登录支持**: 基于 `BaseQRLogin` 的标准化登录器接口
- **定时刷新机制**: 后台自动刷新登录态，基于秒级哈希分配的均匀轮询策略
- **并发状态检查**: 可配置的并发检查数和超时时间

### MCP 协议集成
- **FastMCP 支持**: 完整实现 MCP (Model Context Protocol) 协议
- **HTTP/SSE 传输**: 支持 HTTP、Streamable-HTTP、SSE 三种传输协议
- **动态服务挂载**: 运行时动态创建、更新、删除 MCP 服务
- **提示词版本管理**: 支持为每个工具配置独立的提示词版本

### 数据持久化与审计
- **SQLite/MySQL 支持**: 基于 SQLAlchemy 的 ORM 层，支持多种数据库后端
- **爬虫审计日志**: 完整记录每次爬虫调用的参数、结果、执行时间
- **工具提示词管理**: 提示词版本化管理，支持回滚与切换

### 开发者友好
- **Pydantic 参数验证**: 基于 Pydantic 的参数模型自动验证
- **结果标准化**: 统一的 `SpiderResult` 返回格式
- **反检测支持**: 内置多种反爬检测脚本（Stealth、Permissions Query 等）

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      OmniData Framework                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │  Browser Pool   │  │  Spider Register│  │ Login Register │ │
│  │  (LRU Single)   │  │  (Auto-Discover│  │  (Auto-Discover│ │
│  │  - Single Browser│  │   - LRU Cache)  │  │   - LRU Cache) │ │
│  │  - Context Pool  │  │                 │  │                │ │
│  └────────┬────────┘  └─────────────────┘  └────────────────┘ │
│           │                                                     │
│  ┌────────▼────────┐                                           │
│  │   Redis Store   │  ──► Cookies & localStorage persistence   │
│  └─────────────────┘                                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Server                       │   │
│  │  /api/v1/spiders      - Spider management               │   │
│  │  /api/v1/mcp-services - MCP service management          │   │
│  │  /api/v1/monitor      - Health & metrics                │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 描述 |
|------|------|
| `BrowserContextPool` | 浏览器上下文池，提供 LRU 复用与资源管理 |
| `SpiderRegister` | 爬虫注册器，自动扫描并注册所有爬虫类 |
| `LoginRegister` | 登录器注册器，管理所有登录态刷新任务 |
| `MCPManager` | MCP 服务管理器，支持动态挂载与卸载 |
| `BaseWebSpider` | 爬虫基类，提供标准化的爬虫开发接口 |
| `BaseQRLogin` | 二维码登录基类，提供标准化的登录器接口 |

---

## 快速开始

### 环境要求
- Python 3.10+
- Redis 5.0+ (可选，用于状态持久化)
- SQLite (内置) 或 MySQL

### 安装

```bash
# 克隆项目
git clone https://github.com/noimank/OmniData.git
cd OmniData

# 创建虚拟环境并安装依赖
uv sync

# 安装 Playwright Chromium 浏览器
uv run playwright install chromium
```

### 配置

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

主要配置项：
- `OMNIDATA_BROWSER__HEADLESS`: 浏览器运行模式（true/false）
- `OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE`: Context 池大小（默认 10）
- `OMNIDATA_REDIS__HOST`: Redis 连接地址
- `OMNIDATA_LOGIN__CHECK_CONCURRENCY`: 登录态检查并发数

### 启动服务

```bash
# 启动 API 服务（默认端口 8000）
uv run python main.py

# 或使用 uvicorn
uv run uvicorn omnidata.api.main:app --reload --host 0.0.0.0 --port 8000
```

访问/API 文档：`http://localhost:8000/docs`

---

## 使用示例

### 定义爬虫

```python
from pydantic import BaseModel, Field
from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult

class MySpiderParams(BaseModel):
    url: str = Field(..., description="目标 URL")
    keyword: str = Field(default="", description="搜索关键词")

class MySpider(BaseWebSpider):
    name = "my_spider"
    description = "我的爬虫"
    params_model = MySpiderParams
    platform = "我的平台"
    version = "1.0.0"

    async def crawl(self, params: MySpiderParams) -> SpiderResult:
        async with self.browser_context_pool.get_context() as context:
            page = await context.new_page()
            await page.goto(params.url)
            title = await page.title()
            return SpiderResult(
                success=True,
                data={"title": title, "url": params.url}
            )
```

### API 调用

```bash
# 列出所有爬虫
curl http://localhost:8000/api/v1/spiders

# 运行爬虫
curl -X POST http://localhost:8000/api/v1/spiders/run \
  -H "Content-Type: application/json" \
  -d '{"spider_name": "my_spider", "params": {"url": "https://example.com"}}'

# 创建 MCP 服务
curl -X POST http://localhost:8000/api/v1/mcp-services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-mcp-service",
    "display_name": "My MCP Service",
    "transport": "http",
    "tools": [{"spider_name": "my_spider"}]
  }'
```

---

## 项目结构

```
omnidata/
├── core/                       # 核心模块
│   ├── base_web_spider.py     # 爬虫基类
│   ├── browser_context_pool.py # 浏览器上下文池
│   ├── spider_register.py     # 爬虫注册器
│   ├── login_register.py      # 登录器注册器
│   ├── base_qr_login.py       # 二维码登录基类
│   ├── mcp_manager.py         # MCP 服务管理
│   └── config.py              # 配置管理
├── data_sources/               # 数据源目录（爬虫实现）
│   ├── example/               # 示例爬虫
│   ├── eastmoney/             # 东方财富数据源
│   ├── bilibili/              # 哔哩哔哩数据源
│   └── ...                    # 其他平台
├── database/                   # 数据库模块
│   ├── models.py              # ORM 模型
│   └── session.py             # 会话管理
├── utils/                      # 工具模块
│   ├── redis_client.py        # Redis 客户端
│   └── mcp_utils.py           # MCP 工具
├── api/                        # API 接口
│   ├── routers/               # 路由
│   ├── main.py                # FastAPI 应用
│   └── client.py              # API 客户端
└── tests/                      # 测试目录
```

---

## 配置说明

### 环境变量

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `OMNIDATA_DEBUG` | bool | false | 是否开启调试模式 |
| `OMNIDATA_BROWSER__HEADLESS` | bool | true | 浏览器是否无头运行 |
| `OMNIDATA_BROWSER__DEFAULT_TIMEOUT` | int | 8000 | Playwright 操作超时（毫秒） |
| `OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE` | int | 10 | Context 池最大数量（<=0 禁用） |
| `OMNIDATA_BROWSER__CONTEXT_IDLE_TIMEOUT` | int | 600 | Context 空闲超时（秒，<=0 禁用） |
| `OMNIDATA_REDIS__HOST` | string | localhost | Redis 主机地址 |
| `OMNIDATA_REDIS__PORT` | int | 6379 | Redis 端口 |
| `OMNIDATA_REDIS__DB` | int | 0 | Redis 数据库编号 |
| `OMNIDATA_REDIS__MAX_CONNECTIONS` | int | 10 | Redis 连接池大小 |
| `OMNIDATA_LOGIN__CHECK_CONCURRENCY` | int | 5 | 登录态检查并发数 |
| `OMNIDATA_LOGIN__CHECK_TIMEOUT` | int | 30 | 登录态检查超时（秒） |

---

## API 端点

### 爬虫管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/spiders` | GET | 列出所有爬虫 |
| `/api/v1/spiders/{name}` | GET | 获取爬虫详情 |
| `/api/v1/spiders/{name}/schema` | GET | 获取爬虫参数 Schema |
| `/api/v1/spiders/run` | POST | 运行爬虫 |
| `/api/v1/spiders/run-batch` | POST | 批量运行爬虫 |

### MCP 服务管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/mcp-services` | GET | 列出所有 MCP 服务 |
| `/api/v1/mcp-services` | POST | 创建 MCP 服务 |
| `/api/v1/mcp-services/{id}` | GET | 获取服务详情 |
| `/api/v1/mcp-services/{id}` | PUT | 更新服务 |
| `/api/v1/mcp-services/{id}` | DELETE | 删除服务 |
| `/api/v1/mcp-services/{id}/activate` | PUT | 激活服务 |
| `/api/v1/mcp-services/{id}/deactivate` | PUT | 停用服务 |
| `/api/v1/mcp-services/{id}/tools` | GET | 获取服务工具列表 |
| `/api/v1/mcp-services/{id}/tools` | POST | 添加工具 |
| `/api/v1/mcp-services/{id}/tools/{tool_id}` | DELETE | 移除工具 |
| `/api/v1/mcp-services/spiders/available` | GET | 获取可用 Spider 列表 |

### 登录管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/logins` | GET | 列出所有登录器 |
| `/api/v1/logins/{name}` | GET | 获取登录器详情 |
| `/api/v1/logins/{name}/qrcode` | POST | 获取登录二维码 |

### 监控

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务根信息 |
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/monitor/browser` | GET | 浏览器池统计 |
| `/api/v1/monitor/context` | GET | Context 详细信息 |

---

## 开发指南

### 添加新爬虫

1. 在 `omnidata/data_sources/{platform}/` 下创建 `{name}_spider.py`
2. 继承 `BaseWebSpider` 并实现 `crawl` 方法
3. 可选：实现 `postprocess` 方法进行结果后处理
4. 重新启动服务，爬虫将自动注册

### 添加新登录器

1. 在 `omnidata/data_sources/{platform}/login.py` 中创建登录类
2. 继承 `BaseQRLogin` 并实现二维码获取与登录态检查逻辑
3. 重新启动服务，登录器将自动注册

### 运行测试

```bash
# 类型检查
uv run mypy .

# 代码格式化
uv run black .

# Lint 检查
uv run ruff check .

# 运行测试
uv run pytest tests/ -v --cov=omnidata
```

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

*本项目基于 Playwright 和 FastAPI 构建，遵循 MIT 许可证。*
