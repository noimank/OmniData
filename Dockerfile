# ============================================
# Stage 1: Frontend Build
# ============================================
FROM node:24-alpine AS frontend-builder

WORKDIR /frontend

# 复制依赖文件并安装
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# 复制源码并构建
COPY frontend/ ./
RUN npm run build

# ============================================
# Stage 2: Backend Runtime
# ============================================
FROM python:3.12-slim

# 安装系统依赖、Redis 和 Nginx
RUN apt-get update && apt-get install -y \
    redis-server \
    nginx \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 复制 Python 依赖文件和 README（pyproject.toml 需要它）
COPY pyproject.toml uv.lock README.md ./

# 安装 Python 依赖
RUN uv sync --frozen --no-dev

# 安装 Playwright Chromium 及依赖
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# 复制项目代码
COPY omnidata/ ./omnidata/
COPY main.py ./

# 从前端构建阶段复制构建产物到 Nginx 目录
COPY --from=frontend-builder /frontend/dist /var/www/html/

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/sites-available/default

# 创建数据目录和日志目录
RUN mkdir -p /app/data /var/log/supervisor /var/log/nginx \
    && chown -R www-data:www-data /var/www/html \
    && touch /var/log/nginx/access.log /var/log/nginx/error.log \
    && chown -R www-data:adm /var/log/nginx

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMNIDATA_REDIS__HOST=localhost \
    OMNIDATA_REDIS__PORT=6379 \
    OMNIDATA_BROWSER__HEADLESS=true

# 暴露端口（nginx 对外端口）
EXPOSE 80

# 安装 supervisord
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# 复制 supervisord 配置
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
