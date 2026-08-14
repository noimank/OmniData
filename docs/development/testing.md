# 测试指南

学习如何测试爬虫和登录模块。

---

## 测试框架

- **pytest**：测试框架
- **pytest-asyncio**：异步测试支持
- **pytest-cov**：代码覆盖率

---

## 优先使用 CLI 快速验证爬虫

**重要**：爬虫测试优先使用 CLI 命令进行快速验证，也可在 `tests/data_sources/` 目录下创建 pytest 测试文件进行集成测试。

### 基本测试（无参数）

```bash
uv run python main.py --run <spider_name>
```

### 带参数测试（JSON 格式）

```bash
uv run python main.py --run <spider_name> --params '{"url": "https://example.com", "keyword": "test"}'
```

### 列出所有可用爬虫

```bash
uv run python main.py --list
```

!!! note "注意事项"
    1. `--params` 后必须跟 JSON 字符串，使用单引号包裹
    2. 参数会根据爬虫的 `params_model` 自动验证
    3. 测试结果会直接输出到控制台，包括 `SpiderResult` 的完整信息

---

## 集成测试（tests/data_sources/）

可在 `tests/data_sources/` 下创建测试文件，文件名格式 `test_{platform}.py`。

### 测试 fixture

```python
# tests/data_sources/test_example.py
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import pytest

from omnidata.core.browser_context_pool import BrowserContextPool
from omnidata.core import get_spider_register, close_spider_register
from omnidata.core.config import BrowserConfig
from omnidata.data_sources.example.example_spider import ExampleSpider


@pytest.fixture
async def browser_pool():
    """创建浏览器上下文池实例，完成环境初始化（无头模式）"""
    pool = BrowserContextPool(BrowserConfig(headless=True))
    await pool.initialize()

    # 初始化爬虫注册器
    spider_reg = get_spider_register()
    await spider_reg.initialize()

    yield pool

    # 清理
    await close_spider_register()
    await pool.shutdown()


class TestExampleSpider:
    """测试示例爬虫"""

    async def test_run(self, browser_pool):
        """运行示例爬虫"""
        register = get_spider_register()
        instance = register.get_spider_instance("example_spider")
        result = await instance.run({"url": "https://example.com"})

        assert result.success is True
        assert result.data["title"] is not None

    async def test_invalid_params(self, browser_pool):
        """参数验证失败时返回错误结果（而非抛异常）"""
        register = get_spider_register()
        instance = register.get_spider_instance("example_spider")

        # 缺少必填参数 url
        result = await instance.run({})

        assert result.success is False
        assert result.message is not None
```

### 断言建议

`SpiderResult` 的可用字段：

- `success`：是否成功（bool）
- `data`：返回数据
- `message`：错误信息（`success=False` 时）
- `metadata`：元数据
- `spider_name` / `started_at` / `completed_at` / `duration_seconds`：由 `run()` 自动设置

---

## 运行测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定文件
uv run pytest tests/data_sources/test_example.py -v

# 运行特定测试
uv run pytest tests/data_sources/test_example.py::TestExampleSpider::test_run

# 显示覆盖率
uv run pytest tests/ -v --cov=omnidata
```

---

## 测试最佳实践

1. **CLI 优先**：单爬虫验证用 `uv run python main.py --run`，无需写测试文件
2. **集成测试**：需要断言断言结果时，在 `tests/data_sources/` 下按平台建文件
3. **隔离测试**：每个测试独立运行，使用 fixture 初始化/清理浏览器池
4. **无头模式**：测试中默认使用 `BrowserConfig(headless=True)`
5. **异步测试**：使用 `@pytest.fixture` + `async def` 编写异步 fixture

---

## 下一步

- [部署指南](deployment.md) - 部署到生产环境
