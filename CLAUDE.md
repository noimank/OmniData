# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

OmniData 是一个基于 Playwright 和 FastAPI 的可扩展网页爬虫框架，采用 LRU 单例模式和浏览器上下文池化技术。

**作者**: noimank (noimank@163.com)

## 技术栈

- **Web 框架**: FastAPI 0.128.0+
- **浏览器自动化**: Playwright 1.57.0+
- **缓存**: Redis 5.0.0+
- **ORM**: SQLAlchemy 2.0.45+ (SQLite via aiosqlite)
- **任务调度**: APScheduler 3.11.2+
- **MCP 协议**: FastMCP 2.14.1+
- **包管理**: uv

## 核心命令

```bash
# 安装依赖
uv sync

# 安装 Playwright 浏览器
uv run playwright install chromium

# 启动 API 服务
uv run python main.py                    # 或指定端口
uv run uvicorn omnidata.api.main:app --reload

# 爬虫操作
uv run python main.py --list                           # 列出所有爬虫
uv run python main.py --run <name> --params '{"key": "value"}'  # 运行指定爬虫（传递 JSON 参数）

# 代码质量（只进行格式化，不进行lint和类型检查）
uv run black .                           # 格式化


# 测试
uv run pytest tests/ -v --cov=omnidata

# 文档
uv run mkdocs serve                      # 本地预览
uv run mkdocs build                      # 构建文档
```

## 项目结构

```
omnidata/
├── omnidata/                    # 主包
│   ├── core/                    # 核心模块（LRU 单例）
│   │   ├── base_web_spider.py   # 爬虫基类
│   │   ├── browser_context_pool.py  # 浏览器上下文池
│   │   ├── spider_register.py     # 爬虫注册器
│   │   ├── login_register.py      # 登录器注册器
│   │   ├── base_qr_login.py       # 二维码登录基类
│   │   ├── mcp_manager.py         # MCP 服务管理
│   │   └── config.py              # 配置管理
│   ├── data_sources/            # 数据源目录（爬虫实现）
│   │   └── {platform}/          # 各平台爬虫
│   │       ├── spider.py          # 爬虫主体
│   │       └── login.py           # 登录器（可选）
│   ├── database/                # 数据库模块
│   │   ├── models.py              # ORM 模型
│   │   └── session.py             # 会话管理
│   ├── utils/                   # 工具模块
│   │   ├── redis_client.py        # Redis 客户端
│   │   └── mcp_utils.py           # MCP 工具
│   └── api/                     # API 接口
│       ├── routers/               # 路由
│       └── main.py              # FastAPI 应用
├── frontend/                    # Vue 3 + TypeScript 前端
├── docs/                        # MkDocs 文档
└── tests/                       # 测试目录
```

## 架构特点

1. **LRU 单例模式**: 核心组件使用 `@lru_cache(maxsize=1)` 实现线程安全单例
   - `get_browser_context_pool()` - 浏览器上下文池
   - `get_spider_register()` - 爬虫注册器
   - `get_login_register()` - 登录器注册器

2. **单 Browser + 多 Context**: 共享 Chromium 进程，Context 池化复用

3. **自动注册机制**: 扫描 `data_sources/` 目录自动发现爬虫和登录器

4. **Redis 状态持久化**: cookies 和 localStorage 持久化到 Redis

## 配置

通过环境变量配置（`OMNIDATA_*` 前缀），参考 `.env.example`。

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/spiders` | GET | 列出所有爬虫 |
| `/api/v1/spiders/{name}` | GET | 获取爬虫详情 |
| `/api/v1/spiders/run` | POST | 运行爬虫 |
| `/api/v1/spiders/run-batch` | POST | 批量运行 |
| `/api/v1/mcp/services` | GET | 列出 MCP 服务 |

## 爬虫开发规范

### 基本要求

所有新建爬虫**必须**继承 `omnidata/core/base_web_spider.py` 中的 `BaseWebSpider` 基类。

### 必需属性

```python
class MySpider(BaseWebSpider):
    name = "platform_spider_name"  # 唯一标识，格式：数据源_爬虫功能
    description = "爬虫功能描述"
    platform = "平台中文名"         # 如 "东方财富"
    version = "1.0.0"
    author = "作者名"
    params_model = MyParams         # Pydantic 参数模型（可选）
```

### 必需方法

- `async def crawl(self, params) -> SpiderResult`: 爬取逻辑（**必须实现**）
- `async def postprocess(self, result, params) -> SpiderResult`: 后处理（可选）

### 完整示例

```python
from pydantic import BaseModel, Field
from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult

class MyParams(BaseModel):
    url: str = Field(..., description="目标URL")
    keyword: str = Field(default="", description="搜索关键词")

class MySpider(BaseWebSpider):
    name = "eastmoney_news_query"
    description = "东方财富新闻查询"
    platform = "东方财富"
    version = "1.0.0"
    author = "noimank"
    params_model = MyParams

    async def crawl(self, params: MyParams) -> SpiderResult:
       # new_page() 方法会自动管理上下文，无需手动关闭,参数为对应的平台名字，通常为对应data_sources下的文件夹名字
        async with self.new_page("东方财富") as page:
            try:
                await page.goto(params.url)
                title = await page.title()
                return SpiderResult(
                    success=True,
                    data={"title": title, "url": params.url},
                )
            except Exception as e:
                return SpiderResult(success=False, message=str(e))
            
```

注：编写完成新爬虫任务之后需要使用uv run python main.py --run <name>  来运行爬虫测试,验证爬虫正常工作

### 爬虫测试规范

**重要**: 爬虫测试优先使用 CLI 命令进行快速验证，也可在 `tests/data_sources/` 目录下创建 pytest 测试文件进行集成测试。

#### 测试命令

```bash
# 基本测试（无参数）
uv run python main.py --run <spider_name>

# 带参数测试（JSON 格式）
uv run python main.py --run <spider_name> --params '{"url": "https://example.com", "keyword": "test"}'
```

#### 示例

```bash
# 测试东方财富新闻查询爬虫
uv run python main.py --run eastmoney_news_query --params '{"url": "https://www.eastmoney.com", "keyword": "股票"}'

# 列出所有可用爬虫
uv run python main.py --list
```

#### 注意事项

1. **参数格式**: `--params` 后必须跟 JSON 字符串,使用单引号包裹
2. **参数验证**: 参数会根据爬虫的 `params_model` 自动验证
3. **集成测试**: 可在 `tests/data_sources/` 下创建测试文件，文件名格式 `test_{platform}.py`
4. **调试输出**: 测试结果会直接输出到控制台,包括 `SpiderResult` 的完整信息

### 目录结构

```
omnidata/data_sources/
└── {platform}/           # 平台目录（如 eastmoney/）
    ├── __init__.py
    ├── spider.py         # 爬虫实现
    └── login.py          # 登录器（可选）
```

### 注意事项

1. **命名规范**: `name` 属性格式为 `数据源_功能描述`，如 `eastmoney_news_query`
2. **资源释放**: 使用 `async with` 管理上下文，确保 page 正确关闭
3. **返回格式**: `crawl` 方法必须返回 `SpiderResult` 对象
4. **自动注册**: 放置在 `data_sources/` 目录下会自动被系统发现

## 前端开发规范

### 命令

```bash
cd frontend

# 开发
npm run dev

# 类型检查
npm run type-check

# 构建
npm run build
```

### API 层规范

1. **统一响应格式**: 使用 `ApiResponse<T>` 包装（`success`, `message`, `data`）
2. **函数风格**: 统一使用箭头函数 + 显式返回类型
   ```typescript
   export const getXxx = (id: number): Promise<ApiResponse<Xxx>> => {
     return request.get<ApiResponse<Xxx>>(`/v1/xxx/${id}`)
   }
   ```
3. **例外**: 自包含响应格式（如 `SpiderResult`、`QrcodeResponse`）无需 `ApiResponse` 包装

### Store 层规范

- 错误处理由拦截器统一完成（`request.ts` 中自动 `ElMessage.error()`）
- Store 只需 `console.error()` 记录日志，无需维护 `error` 状态
