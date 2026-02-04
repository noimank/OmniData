<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

## Project

OmniData - 基于 Playwright 和 FastAPI 的可扩展爬虫框架，支持浏览器上下文池管理、自动注册、审计日志和 MCP 协议集成。

**Author:** noimank (康康) - noimank@163.com

## Essential Commands

### Backend (uv)
```bash
uv sync                              # Install dependencies
uv add <package>                     # Add runtime dependency
uv run playwright install chromium   # Install Chromium
uv run python main.py                # Start API server (default: http://0.0.0.0:8380)
uv run python main.py --list         # List all spiders
uv run python main.py --run example_hello       # Run spider for local testing
uv run pytest                        # Run tests
uv run black omnidata/               # Format code
uv run ruff check omnidata/          # Lint code
```

### Frontend
```bash
cd frontend && npm install           # Install dependencies
npm run dev                          # Start dev server (http://localhost:5173)
npm run build                        # Build for production
```

## Architecture

```
omnidata/
├── core/                          # Framework core
│   ├── base_helper.py             # Common base with context management
│   ├── base_web_spider.py         # Abstract spider base class
│   ├── base_qr_login.py           # Abstract QR login base class
│   ├── browser_context_pool.py    # Single Browser + Multi Context pool
│   ├── spider_register.py         # Auto-discovery spiders
│   ├── login_register.py          # Auto-discovery logins
│   ├── mcp_manager.py             # MCP service manager
│   └── config.py                  # Configuration management
├── data_sources/                  # Spider/login implementations (auto-discovered)
│   ├── example/                   # Example spiders
│   ├── bilibili/                  # Bilibili spiders
│   └── eastmoney/                 # EastMoney spiders
├── database/                      # SQLAlchemy + SQLite
│   ├── models.py                  # ORM models (SpiderAudit, MCPService, etc.)
│   └── session.py                 # Async session management
├── api/                           # FastAPI application
│   ├── main.py                    # App with lifespan management
│   ├── routers/                   # API endpoints
│   │   ├── spiders.py             # Spider endpoints
│   │   ├── logins.py              # Login endpoints
│   │   ├── mcp_services.py        # MCP service management
│   │   ├── spider_audit.py        # Audit log & statistics
│   │   ├── spider_prompt_router.py # Spider prompt management
│   │   └── monitor.py             # Browser pool monitoring
│   └── exception_handler.py       # Global exception handlers
├── utils/                         # Utilities
│   ├── redis_client.py            # Redis client wrapper
│   └── anti_detection_scripts.py  # Playwright stealth scripts
└── frontend/                      # Vue 3 frontend
    └── src/
        ├── views/                 # Pages (McpManage, LoginManage, SpiderAudit, Monitor)
        ├── components/            # Reusable components
        ├── stores/                # Pinia state management
        ├── api/                   # API clients
        └── router/                # Vue Router config
```

### Key Patterns

**1. Plugin Auto-Discovery**
- Spiders: Any `*.py` in `omnidata/data_sources/` with class inheriting `BaseWebSpider`
- Logins: Any `login.py` with class inheriting `BaseQRLogin`
- Discovered via recursive file system scanning

**2. Browser Context Pool (单 Browser + 多 Context)**
- Single Chromium browser instance
- Context pooling with LRU cache
- State persistence via Redis (login sessions)
- Automatic cleanup: idle timeout (5min), health check, LRU eviction

**3. BaseHelper Pattern**
- `BaseWebSpider` and `BaseQRLogin` inherit from `BaseHelper`
- Key methods:
  - `async with self.new_page(namespace)` - Auto-managed Page with anti-detection
  - `await self.get_context(namespace)` - Get Context (manual Page management)
  - `await self.save_context_state(context, namespace)` - Save to Redis

**4. Spider Execution Flow**
- `run(params)` → validate → `crawl()` → `postprocess()` → audit log
- Returns `SpiderResult` with metadata
- Automatic audit logging to SQLite

**5. MCP Integration**
- Dynamic MCP server creation from spider selection
- Transports: http, streamable-http, sse
- Services mount at `/mcp/{service_name}`
- Customizable tool descriptions via web UI
- Multi-version prompt support per spider

**6. Lifecycle Management**
- FastAPI `lifespan` handles init/shutdown
- Cleanup order: MCP → DB → logins → spiders → context pool → Redis

## Spider Template

```python
from pydantic import BaseModel, Field
from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult

class MyParams(BaseModel):
    url: str = Field(..., description="Target URL")

class MySpider(BaseWebSpider):
    name = "platform_action"         # Format: {platform}_{action}
    description = "Spider description"
    version = "1.0.0"
    author = "your_name"
    platform = "Platform Name"        # Chinese
    params_model = MyParams

    async def crawl(self, params: MyParams) -> SpiderResult:
        async with self.new_page(namespace="my_namespace") as page:
            await page.goto(params.url)
            return SpiderResult(
                success=True,
                data={"title": await page.title()}
            )
```

## Configuration

Environment-based via `pydantic-settings`:
- Prefix: `OMNIDATA_`
- Delimiter: `__`

```bash
# Browser
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE=10

# Redis
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379

# Database
OMNIDATA_DB__PATH=omnidata.db
```

## API Endpoints

### Core
- `GET /spiders` - List spiders
- `POST /spiders/run` - Run spider
- `POST /spiders/run-batch` - Batch run with concurrency
- `GET /monitor/browser-pool` - Context pool stats

### Audit
- `GET /api/v1/spider-audit/stats` - Statistics
- `GET /api/v1/spider-audit/records` - Query records (paginated)
- `DELETE /api/v1/spider-audit/cleanup` - Cleanup old records

### MCP
- `GET /api/v1/mcp-services` - List services
- `POST /api/v1/mcp-services` - Create service
- `GET /api/v1/mcp-services/{id}/prompts` - Get tool prompts
- `PUT /api/v1/mcp-services/{id}/tools/{tool_id}/prompt` - Update prompt

## Code Style

- **Line length:** 100 chars
- **Python:** >= 3.12
- **Type hints:** Required
- **Doc language:** Chinese

## Tech Stack

**Backend:** Python 3.12, FastAPI, Playwright (Chromium), Redis, SQLAlchemy, FastMCP

**Frontend:** Vue 3.5, TypeScript, Element Plus, Pinia, Vite

**Dev:** uv, Black, Ruff, MyPy, pytest
