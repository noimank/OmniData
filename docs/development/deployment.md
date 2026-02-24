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

### 1. 使用项目提供的 Dockerfile

```bash
# 构建镜像
docker build -t omnidata:latest .

# 运行容器
docker run -d \
  --name omnidata \
  -p 8380:8380 \
  -e OMNIDATA_REDIS__HOST=host.docker.internal \
  -e OMNIDATA_BROWSER__HEADLESS=true \
  omnidata:latest
```

### 2. 使用 Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  omnidata:
    build: .
    ports:
      - "8380:8380"
    environment:
      - OMNIDATA_REDIS__HOST=redis
      - OMNIDATA_BROWSER__HEADLESS=true
    depends_on:
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - omnidata
```

启动：

```bash
docker-compose up -d
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
OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE=20

# API
OMNIDATA_API__HOST=0.0.0.0
OMNIDATA_API__PORT=8380
OMNIDATA_API__WORKERS=4
```

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
curl http://localhost:8380/monitor/browser-pool
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

```bash
# 根据 CPU 核心数调整
OMNIDATA_API__WORKERS=4
```

### 2. 增加 Context Pool 大小

```bash
OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE=20
```

### 3. 启用缓存

```bash
# Redis 缓存
OMNIDATA_REDIS__CACHE_TTL=3600
```

### 4. 数据库优化

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
