# 常见问题

解答常见问题和疑惑。

---

## 安装与配置

### Q: 如何安装 Playwright 浏览器？

```bash
uv run playwright install chromium
```

### Q: Redis 连接失败怎么办？

检查 Redis 是否运行：

```bash
redis-cli ping
# 应返回 PONG
```

启动 Redis：

```bash
# Windows
redis-server

# Linux/macOS
sudo systemctl start redis
```

### Q: 如何修改监听端口？

在 `.env` 文件中设置：

```bash
OMNIDATA_API__PORT=8381
```

---

## 使用问题

### Q: 爬虫返回空数据？

1. 检查目标网站是否可访问
2. 检查参数是否正确
3. 查看审计日志中的错误信息

```bash
curl http://localhost:8380/api/v1/spider-audit/records?spider_name=xxx&limit=10
```

### Q: 如何提高爬取速度？

1. 增加浏览器池大小：
   ```bash
   OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE=20
   ```

2. 使用批量运行：
   ```bash
   POST /spiders/run-batch
   ```

### Q: 需要登录的网站如何处理？

使用二维码登录功能：

```bash
# 1. 启动登录
curl -X POST http://localhost:8380/logins/start \
  -H "Content-Type: application/json" \
  -d '{"login_name": "bilibili"}'

# 2. 获取二维码后扫码

# 3. 检查登录状态
curl http://localhost:8380/logins/status/bilibili
```

---

## MCP 相关

### Q: 如何在 Claude Desktop 中使用？

编辑 Claude Desktop 配置文件：

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "omnidata": {
      "url": "http://localhost:8380/mcp/financial-data",
      "transport": "sse"
    }
  }
}
```

### Q: MCP 服务返回错误？

1. 检查服务是否创建成功
2. 检查爬虫是否可用
3. 查看 MCP 服务日志

---

## 部署问题

### Q: Docker 容器无法连接 Redis？

使用 Docker Compose：

```yaml
services:
  redis:
    image: redis:alpine
  omnidata:
    environment:
      - OMNIDATA_REDIS__HOST=redis
```

### Q: 生产环境建议配置？

```bash
# 浏览器
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE=20

# API
OMNIDATA_API__WORKERS=4

# 审计日志
OMNIDATA_AUDIT__RETENTION_DAYS=30
```

---

## 其他问题

### Q: 如何贡献代码？

欢迎提交 Pull Request！

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

### Q: 商业使用可以吗？

本项目采用 MIT 许可证，可以商业使用。

### Q: 如何获取支持？

- GitHub Issues: https://github.com/noimank/OmniData/issues
- Email: noimank@163.com
