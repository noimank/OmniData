# 测试指南

学习如何测试爬虫和登录模块。

---

## 测试框架

- **pytest**：测试框架
- **pytest-asyncio**：异步测试支持
- **pytest-cov**：代码覆盖率

---

## 测试爬虫

### 基础测试

```python
# tests/test_spiders.py
import pytest
from omnidata.core.spider_register import SpiderRegister
from omnidata.data_sources.example.example_spider import ExampleHelloSpider, HelloParams

@pytest.mark.asyncio
async def test_example_spider():
    """测试示例爬虫"""
    spider = ExampleHelloSpider()

    result = await spider.run(
        params={"name": "Test"}
    )

    assert result.success is True
    assert result.data["message"] == "Hello, Test!"
```

### 参数验证测试

```python
@pytest.mark.asyncio
async def test_invalid_params():
    """测试参数验证"""
    spider = ExampleHelloSpider()

    # 缺少必填参数
    with pytest.raises(ValidationError):
        await spider.run(params={})
```

### Mock 测试

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    """使用 Mock 测试"""
    spider = ExampleHelloSpider()

    # Mock new_page 方法
    with patch.object(spider, 'new_page') as mock_page:
        mock_page.return_value.__aenter__.return_value = AsyncMock()

        result = await spider.run(params={"name": "Test"})

        assert result.success is True
        mock_page.assert_called_once()
```

---

## 测试登录

```python
# tests/test_logins.py
import pytest
from omnidata.core.login_register import LoginRegister
from omnidata.data_sources.bilibili.login import BilibiliLogin

@pytest.mark.asyncio
async def test_bilibili_login_get_qr():
    """测试获取二维码"""
    login = BilibiliLogin()

    qr_id = await login.get_qr_code()

    assert qr_id is not None
    assert qr_id.startswith("bilibili_")

@pytest.mark.asyncio
async def test_bilibili_login_wait():
    """测试等待登录（需要手动扫码）"""
    login = BilibiliLogin()

    # 这个测试需要手动扫码
    # 在 CI/CD 中应该被跳过
    pytest.skip("需要手动扫码")

    result = await login.wait_for_login()

    assert result["status"] == "success"
```

---

## 测试 fixtures

```python
# tests/conftest.py
import pytest
from omnidata.core.spider_register import SpiderRegister

@pytest.fixture
async def spider_register():
    """爬虫注册器 fixture"""
    register = SpiderRegister()
    await register.initialize()
    yield register
    await register.cleanup()

@pytest.fixture
def example_spider():
    """示例爬虫 fixture"""
    return SpiderRegister.get_spider("example_hello")
```

---

## 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定文件
uv run pytest tests/test_spiders.py

# 运行特定测试
uv run pytest tests/test_spiders.py::test_example_spider

# 显示输出
uv run pytest -v

# 生成覆盖率报告
uv run pytest --cov=omnidata --cov-report=html
```

---

## 集成测试

### 测试 API

```python
# tests/test_api.py
import pytest
from httpx import AsyncClient
from omnidata.api.main import app

@pytest.mark.asyncio
async def test_list_spiders():
    """测试列出所有爬虫"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/spiders")

        assert response.status_code == 200
        assert "spiders" in response.json()

@pytest.mark.asyncio
async def test_run_spider():
    """测试运行爬虫"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/spiders/run",
            json={
                "spider_name": "example_hello",
                "params": {"name": "Test"}
            }
        )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
```

---

## 测试最佳实践

1. **隔离测试**：每个测试独立运行
2. **使用 Mock**：避免真实网络请求
3. **清理资源**：使用 fixture 清理
4. **覆盖率目标**：保持 80% 以上覆盖率
5. **异步测试**：使用 `@pytest.mark.asyncio`

---

## CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run tests
        run: uv run pytest --cov=omnidata

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 下一步

- [部署指南](deployment.md) - 部署到生产环境
