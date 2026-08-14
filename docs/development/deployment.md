# 部署指南

将 OmniData 部署到生产环境。

---

## 环境要求

- **Python**：3.12+
- **Redis**：5.0+
- **内存**：建议 2GB+
- **CPU**：建议 2 核心以上

---

## Docker 部署

镜像为**一体化镜像**：内置 Redis、Nginx、后端（supervisord 统一管理），对外只暴露 **80** 端口。

### 1. 使用已发布镜像（推荐）

```bash
docker run -d \
  --name omnidata \
  -p 80:80 \
  -e TZ=Asia/Shanghai \
  -v ./data:/app/data \
  -v ./logs:/var/log/supervisor \
  --restart unless-stopped \
  noimankdocker/omnidata:latest
```

访问：
- 前端界面：`http://localhost`
- API 文档：`http://localhost/docs`

!!! tip "数据持久化"
    项目使用 SQLite 数据库（位于 `/app/data/omnidata.db`），建议把 `/app/data` 挂载到本地，防止容器重建造成数据丢失。

### 2. 使用项目提供的 Dockerfile 本地构建

```bash
# 构建镜像
docker build -t omnidata:latest .

# 运行容器
docker run -d \
  --name omnidata \
  -p 80:80 \
  -v ./data:/app/data \
  -e OMNIDATA_BROWSER__HEADLESS=true \
  omnidata:latest
```

### 3. 使用 Docker Compose

```yaml
services:
  omnidata:
    image: noimankdocker/omnidata:latest   # 或改为 build: .
    container_name: omnidata
    ports:
      - "80:80"
    volumes:
      - ./data:/app/data
      - ./logs:/var/log/supervisor
    environment:
      - TZ=Asia/Shanghai
      - OMNIDATA_BROWSER__HEADLESS=true
    restart: unless-stopped
```

启动：

```bash
docker compose up -d
```

---

## 服务器部署

### 1. 安装依赖

```bash
# 安装 Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv

# 安装 Redis
sudo apt install redis-server
sudo systemctl start redis
```

### 2. 部署应用

```bash
# 克隆代码
git clone https://github.com/noimank/OmniData.git
cd OmniData

# 安装依赖
pip install uv
uv sync

# 安装 Playwright 浏览器
uv run playwright install chromium --with-deps
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

生产环境建议配置：

```bash
# Redis
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379
OMNIDATA_REDIS__PASSWORD=your_password

# 浏览器
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__DEFAULT_TIMEOUT=8000

# 登录器
OMNIDATA_LOGIN__CHECK_CONCURRENCY=5
OMNIDATA_LOGIN__CHECK_TIMEOUT=30
```

!!! note
    浏览器池容量、空闲回收、整体回收、自愈等机制为内核固定策略，**不提供环境变量配置**。

### 4. 使用 Supervisor 管理进程

```bash
# 安装 Supervisor
sudo apt install supervisor

# 创建配置
sudo nano /etc/supervisor/conf.d/omnidata.conf
```

```ini
[program:omnidata]
command=/path/to/OmniData/.venv/bin/python main.py
directory=/path/to/OmniData
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/omnidata.err.log
stdout_logfile=/var/log/omnidata.out.log
environment=OMNIDATA_REDIS__HOST="localhost"
```

启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start omnidata
```

---

## 反向代理配置

### Nginx

```nginx
upstream omnidata {
    server 127.0.0.1:8380;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://omnidata;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /mcp/ {
        proxy_pass http://omnidata;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 监控

### 健康检查

```bash
curl http://localhost:8380/health
```

### 浏览器池监控

```bash
curl http://localhost:8380/api/v1/monitor/browser-pool
```

### 日志查看

```bash
# Supervisor 日志
sudo tail -f /var/log/omnidata.out.log

# Docker 日志
docker logs -f omnidata
```

---

## 性能优化

### 1. 调整 Worker 数量

> 本地开发模式下通过 `uv run python main.py --port 8380` 指定端口启动。
> 生产部署建议使用 Docker 镜像（supervisord + uvicorn 管理），或通过 gunicorn/uvicorn 多进程方式部署。

### 2. 浏览器池

浏览器池容量、空闲回收、整体回收、自愈等为内核固定策略，自动运行，**无需也不支持调整**。

### 3. 数据库优化

```bash
# 定期清理旧审计日志
DELETE /api/v1/spider-audit/cleanup?days=30
```

---

## 安全建议

1. **使用环境变量**：敏感信息不要写入代码
2. **限制访问**：使用防火墙限制访问来源
3. **HTTPS**：生产环境使用 SSL 证书
4. **定期更新**：保持依赖包最新版本
5. **监控日志**：定期检查异常日志

---

## 下一步

- [配置参考](configuration.md) - 详细配置说明
