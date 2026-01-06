# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

OmniData is a scalable web scraping framework built with Playwright and FastAPI. It provides an extensible architecture with browser pool management, automatic spider/login registration, and a plugin-based system.

**Author:** noimank (康康) - noimank@163.com

## Essential Commands

### Package Management (using uv)
```bash
uv sync                              # Install dependencies
uv add <package>                     # Add runtime dependency
uv add --dev <package>               # Add dev dependency
```

### Playwright Setup
```bash
uv run playwright install chromium   # Install Chromium browser (only supported browser)
```

### Development Server
```bash
uv run python main.py                # Start API server (default: http://0.0.0.0:8380)
uv run python main.py --reload       # Start with auto-reload
uv run python main.py --host 0.0.0.0 --port 8380  # Custom host/port
```

### Spider Management
```bash
uv run python main.py --list         # List all registered spiders
uv run python main.py --run <spider_name> --params '{"url": "..."}'  # Run a spider
```

### Frontend Development
```bash
cd frontend
npm install                          # Install frontend dependencies
npm run dev                          # Start dev server (default: http://localhost:5173)
npm run build                        # Build for production
npm run preview                      # Preview production build
```

### Testing & Code Quality
```bash
uv run pytest                        # Run tests
uv run pytest --cov=omnidata         # Run with coverage
uv run black omnidata/               # Format code
uv run ruff check omnidata/          # Lint code
uv run mypy omnidata/                # Type checking
```

## Architecture

### High-Level Structure

```
omnidata/
├── core/                    # Framework core
│   ├── base_helper.py       # Common helper base class with context management
│   ├── base_web_spider.py   # Abstract base class for all spiders
│   ├── base_qr_login.py     # Abstract base class for QR login handlers
│   ├── browser_pool.py      # Browser connection pool manager
│   ├── spider_register.py   # Auto-discovery and registration for spiders
│   ├── login_register.py    # Auto-discovery and registration for logins
│   ├── config.py            # Configuration management
│   └── exceptions.py        # Custom exceptions
├── data_sources/            # Spider and login implementations (auto-discovered)
│   ├── example/             # Example spiders
│   ├── bilibili/            # Bilibili data source (spiders + login)
│   └── eastmoney/           # EastMoney data source (spiders + login)
├── utils/                   # Utilities
│   ├── redis_client.py      # Redis client wrapper
│   └── anti_detection_scripts.py  # Playwright anti-detection scripts
├── api/                     # FastAPI application
│   ├── main.py              # FastAPI app with lifespan management
│   ├── routers/             # API route handlers
│   │   ├── spiders.py       # Spider endpoints
│   │   ├── logins.py        # Login endpoints
│   │   ├── monitor.py       # Browser pool monitoring
│   │   ├── auth.py          # Authentication endpoints
│   │   └── health.py        # Health check
│   └── middleware/          # Custom middleware
│       └── auth.py          # API key authentication
└── frontend/                # Vue 3 frontend
    └── src/
        ├── views/           # Page components
        ├── components/      # Reusable components
        ├── stores/          # Pinia state management
        ├── api/             # API client and types
        └── router/          # Vue Router configuration
```

### Key Patterns

**1. Plugin-Based Auto-Discovery**
- Spiders: Any `*.py` file in `omnidata/data_sources/` with classes inheriting `BaseWebSpider`
- Logins: Any `login.py` file with classes inheriting `BaseQRLogin`
- No manual registration required
- Discovered via recursive file system scanning

**2. Browser Pool Management**
- Multi-instance Chromium pool with round-robin allocation
- Automatic cleanup and restart of idle browsers (configurable timeout)
- Context state persistence via Redis for login sessions
- Connection pooling with configurable initial size

**3. BaseHelper Inheritance Pattern**
- Both `BaseWebSpider` and `BaseQRLogin` inherit from `BaseHelper`
- Provides common context management methods:
  - `async with self.get_context(namespace)` - Auto-managed browser context
  - `self.get_context_simple(namespace)` - Manual context management
  - `self.save_context_state(context, namespace)` - Save cookies/state to Redis
  - `self.apply_anti_detection_scripts(page, scripts)` - Apply stealth scripts

**4. QR Login System**
- `BaseQRLogin` provides framework for implementing QR code login flows
- Four abstract methods to implement:
  - `get_qrcode(qr_type)` - Return QR code image/URL
  - `verify_login_state()` - Poll for login completion
  - `is_login()` - Check if currently logged in (uses separate context)
  - `get_qrcode_types()` - Return supported login methods
- Auto-refresh: Login state refreshed to Redis every hour via background task
- Login state stored in Redis with configurable TTL (default 7 days)

**5. Dependency Injection**
- BrowserPool injected into spiders/logins via constructor
- Global singletons managed via async locks (`get_spider_register`, `get_login_register`)

**6. Lifecycle Management**
- FastAPI `lifespan` context manager handles all initialization/shutdown
- Proper cleanup order: logins → spiders → browser pool → Redis

## Spider Creation Template

All spiders must be placed in `omnidata/data_sources/` (in any subdirectory) and follow this pattern:

```python
from pydantic import BaseModel, Field
from omnidata.core.base_web_spider import BaseWebSpider

class MyParams(BaseModel):
    url: str = Field(..., description="Target URL")

class MySpider(BaseWebSpider):
    name = "my_spider"                    # Unique identifier (use format: platform_action)
    description = "My spider description"  # Documentation
    version = "1.0.0"                     # Semantic version
    author = "your_name"                  # Author
    platform = "My Platform"              # Platform name (Chinese)
    params_model = MyParams               # Optional: Pydantic model for validation

    async def crawl(self, params: MyParams) -> dict | list[dict]:
        async with self.get_context(namespace="my_namespace") as context:
            page = await context.new_page()
            await page.goto(params.url)
            return {"title": await page.title()}
```

**Important naming convention:**
- `name` should follow pattern: `{platform}_{action}` (e.g., `bilibili_video_info`, `eastmoney_stock_query`)
- File location: `omnidata/data_sources/{platform}/{spider_name}.py`

## QR Login Creation Template

QR login handlers must be placed in `omnidata/data_sources/{platform}/login.py`:

```python
from omnidata.core.base_qr_login import BaseQRLogin, QRLoginState, QRCode

class MyPlatformLogin(BaseQRLogin):
    name = "my_platform_login"     # This becomes the Redis namespace
    platform = "MyPlatform"        # Platform name (Chinese)

    async def get_qrcode_types(self) -> list[str]:
        """Return supported login methods"""
        return ["微信", "App"]

    async def get_qrcode(self, qr_type: str) -> QRCode:
        """Get QR code - use self._qr_page and self._qr_context"""
        if not self._qr_context:
            browser = await self.browser_pool.get_browser()
            self._qr_context = await browser.new_context()
            self._qr_page = await self._qr_context.new_page()

        await self._qr_page.goto("https://example.com/login")
        qr_url = await self._qr_page.get_attribute("#qrcode img", "src")

        return QRCode(success=True, url=qr_url, qr_type=qr_type)

    async def verify_login_state(self) -> QRLoginState:
        """Poll for login completion - uses self._qr_page"""
        success = await self._qr_page.query_selector(".user-avatar") is not None
        if success:
            await self.save_context_state(self._qr_context, self.name)
        return QRLoginState(status="success" if success else "waiting")

    async def is_login(self) -> QRLoginState:
        """Check if logged in - uses separate context"""
        async with self.get_context(namespace=self.name) as context:
            page = await context.new_page()
            await page.goto("https://example.com")
            logged_in = await page.query_selector(".user-avatar") is not None
            return QRLoginState(status="success" if logged_in else "not_logged_in")

    async def refresh_login_state(self) -> None:
        """Refresh saved login state to Redis"""
        if self._qr_context:
            await self.save_context_state(self._qr_context, self.name)
```

## Configuration

Environment-based configuration via `pydantic-settings`:
- Prefix: `OMNIDATA_`
- Nested delimiter: `__`

Key settings:
```bash
# Browser
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__POOL_INITIAL_SIZE=2
OMNIDATA_BROWSER__IDLE_TIMEOUT=300
OMNIDATA_BROWSER__LAUNCH_TIMEOUT=30

# Redis
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379
OMNIDATA_REDIS__DB=0
OMNIDATA_REDIS__PASSWORD=
OMNIDATA_REDIS__CONTEXT_STATE_TTL=604800  # 7 days

# Auth
OMNIDATA_AUTH__API_KEY=your_api_key_here

# Login
OMNIDATA_LOGIN__CHECK_CONCURRENCY=5
OMNIDATA_LOGIN__CHECK_TIMEOUT=30
```

## Code Style

- **Line length:** 100 characters (Black and Ruff)
- **Python version:** 3.12+
- **Naming:** PascalCase for classes, snake_case for functions/methods
- **Type hints:** Required (MyPy strict mode enabled)
- **Language:** Documentation uses Chinese

## Constraints

- **Browser:** Only Chromium is supported (hardcoded in `browser_pool.py`)
- **Spider directory:** Must be `omnidata/data_sources/` (computed relative to `core/`)
- **Login file naming:** Must be named `login.py` to be auto-discovered
- **Python:** Requires Python >= 3.12
- **User Agent:** Fixed UA in `base_helper.py` - change carefully for anti-detection

## API Endpoints

### Spiders
- `GET /spiders` - List all registered spiders
- `GET /spiders/{spider_name}` - Get spider details
- `POST /spiders/run` - Run a single spider
- `POST /spiders/run-batch` - Run multiple spiders with concurrency control

### Logins
- `GET /logins` - List all login handlers with status
- `GET /logins/{login_name}` - Get login details
- `GET /logins/{login_name}/qrcode-types` - Get supported QR code types
- `POST /logins/{login_name}/qrcode` - Get QR code for login
- `POST /logins/{login_name}/verify` - Verify login status
- `GET /logins/{login_name}/status` - Check current login status
- `DELETE /logins/{login_name}/state` - Clear saved login state

### Monitor
- `GET /monitor/browser-pool` - Get browser pool statistics

### Auth
- `POST /auth/set-api-key` - Set API key for authentication

## Tech Stack

**Backend:**
- Python 3.12
- FastAPI 0.128.0
- Playwright 1.57.0 (Chromium only)
- Redis 5.0.0+
- Pydantic 2.0+
- Pydantic-Settings 2.0+

**Frontend:**
- Vue 3.5
- TypeScript 5.5
- Element Plus 2.13
- Pinia 2.2
- Vue Router 4.4
- Vite 6.0
- Axios 1.7

**Development:**
- uv (package management)
- Black 24.0 (code formatting)
- Ruff 0.3 (linting)
- MyPy 1.9 (type checking)
- pytest 8.0 (testing)
