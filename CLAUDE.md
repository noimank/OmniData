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
uv run python main.py --list             # 列出所有爬虫
uv run python main.py --run <name>       # 运行指定爬虫

# 代码质量
uv run mypy .                            # 类型检查
uv run black .                           # 格式化
uv run ruff check .                      # lint

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
│       ├── main.py                # FastAPI 应用
│       └── client.py              # API 客户端
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
