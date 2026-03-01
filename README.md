# OmniData

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-green.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-1.57+-blue.svg)](https://playwright.dev/)

OmniData 是一个企业级的可扩展网页爬虫框架，基于 Playwright 和 FastAPI 构建，提供强大的浏览器自动化能力、智能登录态管理以及 MCP 协议集成支持。

**作者**: noimank (noimank@163.com)

**完整文档**: https://noimank.github.io/OmniData/

---

## 特性

- **浏览器自动化**: 基于 Playwright 实现完整的浏览器自动化能力，支持 Headers、Cookie、LocalStorage 等全流程控制
- **LRU 单例模式**: 核心组件使用 LRU 缓存实现线程安全单例，优化资源管理
- **Context 池化**: 单 Browser 多 Context 架构，Context 自动复用与回收，显著降低内存占用
- **自动注册机制**: 扫描 `data_sources/` 目录自动发现爬虫和登录器，轻松拓展爬虫任务，零配置启动
- **Redis 状态持久化**: cookies 和 localStorage 自动持久化到 Redis，支持登录态长期保持
- **MCP 协议集成**: 完整实现 MCP (Model Context Protocol) 协议，支持 HTTP/SSE 传输，自由选择任意多个爬虫接口任意组成多个mcp服务
- **智能登录管理**: 二维码登录支持、定时刷新机制、并发状态检查

---

## 快速开始

### Docker 部署（推荐）

```bash
docker run -d \
  --name omnidata \
  -p 80:80 \
  -e TZ=Asia/Shanghai \
  -v ./data:/app/data -v ./logs:/var/log/supervisor \
  --restart unless-stopped \
  noimankdocker/omnidata:latest
```

详细的环境配置请参考.env.example 文件。项目使用sqlite数据库，建议把/app/data目录挂载到本地，防止容器重建造成数据丢失


访问服务：
- 前端界面：`http://localhost`
- API 文档：`http://localhost:8000/docs`

### 本地开发

```bash
# 克隆项目
git clone https://github.com/noimank/OmniData.git
cd OmniData

# 安装依赖
uv sync

# 安装 Playwright 浏览器
uv run playwright install chromium

# 配置环境变量
cp .env.example .env

# 启动服务
uv run python main.py
```

---

## 使用示例

### 定义爬虫

```python
from pydantic import BaseModel, Field
from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult

class MySpiderParams(BaseModel):
    url: str = Field(..., description="目标 URL")

class MySpider(BaseWebSpider):
    name = "my_spider"
    description = "我的爬虫"
    params_model = MySpiderParams

    async def crawl(self, params: MySpiderParams) -> SpiderResult:
        async with self.browser_context_pool.get_context() as context:
            page = await context.new_page()
            await page.goto(params.url)
            title = await page.title()
            return SpiderResult(success=True, data={"title": title})
```

### API 调用

```bash
# 列出所有爬虫
curl http://localhost:8000/api/v1/spiders

# 运行爬虫
curl -X POST http://localhost:8000/api/v1/spiders/run \
  -H "Content-Type: application/json" \
  -d '{"spider_name": "my_spider", "params": {"url": "https://example.com"}}'
```

---

## 项目结构

```
omnidata/
├── core/                       # 核心模块（爬虫基类、上下文池、注册器）
├── data_sources/               # 数据源目录（爬虫实现）
├── database/                   # 数据库模块
├── utils/                      # 工具模块
├── api/                        # API 接口
└── tests/                      # 测试目录
```

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。
