# 快速开始

5 分钟快速上手 OmniData。

---

## 环境要求

- **Python**：3.12 或更高版本
- **Redis**：5.0 或更高版本
- **Node.js**：18+（仅前端需要）

---

## 1. 克隆项目

```bash
git clone https://github.com/noimank/OmniData.git
cd OmniData
```

---

## 2. 安装依赖

```bash
# 安装 Python 依赖
uv sync

# 安装 Playwright 浏览器
uv run playwright install chromium
```

---

## 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
```

`.env` 最小配置：

```bash
# Redis 配置
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379
OMNIDATA_REDIS__DB=0

# 浏览器配置
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE=10
```

---

## 4. 启动服务

### 后端服务

```bash
uv run python main.py
```

服务启动在 `http://localhost:8380`

### 前端服务（可选）

```bash
cd frontend
npm install
npm run dev
```

前端界面在 `http://localhost:5173`

---

## 5. 测试 API

### 列出所有爬虫

```bash
curl http://localhost:8380/spiders
```

### 运行示例爬虫

```bash
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "example_hello",
    "params": {
      "name": "OmniData"
    }
  }'
```

### 查看 API 文档

访问 `http://localhost:8380/docs` 查看自动生成的 OpenAPI 文档。

---

## 验证安装

```bash
# 运行测试
uv run pytest

# 查看浏览器池状态
curl http://localhost:8380/monitor/browser-pool
```

---

## 常见问题

### Redis 连接失败

```bash
# 检查 Redis 是否运行
redis-cli ping

# 启动 Redis
# Windows
redis-server

# Linux/macOS
sudo systemctl start redis
```

### Playwright 浏览器未安装

```bash
# 重新安装
uv run playwright install chromium
```

### 端口冲突

修改 `.env` 文件：

```bash
OMNIDATA_API__PORT=8381
```

---

## 下一步

- [创建爬虫](creating-spider.md) - 开发你的第一个爬虫
- [添加登录](adding-login.md) - 处理需要登录的网站
- [部署指南](deployment.md) - 部署到生产环境

---

## 使用 Docker（可选）

```bash
# 构建镜像
docker build -t omnidata .

# 运行容器
docker run -d \
  -p 8380:8380 \
  -e OMNIDATA_REDIS__HOST=host.docker.internal \
  omnidata
```
