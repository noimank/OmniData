# 配置参考

OmniData 的完整配置说明。

---

## 配置方式

OmniData 使用 `pydantic-settings` 管理配置，支持：

- **环境变量**：优先级最高
- **.env 文件**：开发环境推荐
- **默认值**：代码中的默认配置

---

## 环境变量格式

- **前缀**：`OMNIDATA_`
- **分隔符**：`__` (双下划线)
- **示例**：
  ```bash
  OMNIDATA_BROWSER__HEADLESS=true
  OMNIDATA_REDIS__HOST=localhost
  ```

---

## 浏览器配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_BROWSER__HEADLESS` | `true` | 无头模式 |
| `OMNIDATA_BROWSER__CHANNEL` | `chromium` | 浏览器类型 |
| `OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE` | `10` | Context 池最大容量 |
| `OMNIDATA_BROWSER__CONTEXT_POOL_IDLE_TIMEOUT` | `300` | 空闲超时（秒） |
| `OMNIDATA_BROWSER__USER_DATA_DIR` | `null` | 用户数据目录 |
| `OMNIDATA_BROWSER__DEVTOOLS` | `false` | 是否启用开发者工具 |

```bash
# 示例
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE=20
OMNIDATA_BROWSER__CONTEXT_POOL_IDLE_TIMEOUT=600
```

---

## Redis 配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_REDIS__HOST` | `localhost` | Redis 主机 |
| `OMNIDATA_REDIS__PORT` | `6379` | Redis 端口 |
| `OMNIDATA_REDIS__DB` | `0` | Redis 数据库编号 |
| `OMNIDATA_REDIS__PASSWORD` | `null` | Redis 密码 |
| `OMNIDATA_REDIS__PREFIX` | `omnidata:` | 键前缀 |
| `OMNIDATA_REDIS__STATE_TTL` | `86400` | 状态过期时间（秒） |

```bash
# 示例
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379
OMNIDATA_REDIS__PASSWORD=your_password
OMNIDATA_REDIS__PREFIX=omnidata:
```

---

## 数据库配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_DB__PATH` | `omnidata.db` | SQLite 数据库文件路径 |
| `OMNIDATA_AUDIT__RETENTION_DAYS` | `90` | 审计日志保留天数 |

```bash
# 示例
OMNIDATA_DB__PATH=/var/lib/omnidata/omnidata.db
OMNIDATA_AUDIT__RETENTION_DAYS=30
```

---

## API 配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_API__HOST` | `0.0.0.0` | API 监听地址 |
| `OMNIDATA_API__PORT` | `8380` | API 监听端口 |
| `OMNIDATA_API__WORKERS` | `1` | Worker 进程数 |
| `OMNIDATA_API__RELOAD` | `false` | 开发模式热重载 |

```bash
# 示例
OMNIDATA_API__HOST=0.0.0.0
OMNIDATA_API__PORT=8380
OMNIDATA_API__WORKERS=4
```

---

## 爬虫配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_SPIDER__RETRY_TIMES` | `3` | 重试次数 |
| `OMNIDATA_SPIDER__RETRY_DELAY` | `1` | 重试延迟（秒） |
| `OMNIDATA_SPIDER__TIMEOUT` | `30` | 默认超时（秒） |

```bash
# 示例
OMNIDATA_SPIDER__RETRY_TIMES=5
OMNIDATA_SPIDER__RETRY_DELAY=2
OMNIDATA_SPIDER__TIMEOUT=60
```

---

## MCP 配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_MCP__DEFAULT_TRANSPORT` | `streamable-http` | 默认传输协议 |
| `OMNIDATA_MCP__ROUTE_PREFIX` | `/mcp/` | 路由前缀 |

```bash
# 示例
OMNIDATA_MCP__DEFAULT_TRANSPORT=streamable-http
OMNIDATA_MCP__ROUTE_PREFIX=/mcp/
```

---

## 健康检查配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_BROWSER__HEALTH_CHECK_INTERVAL` | `60` | 检查间隔（秒） |
| `OMNIDATA_BROWSER__HEALTH_CHECK_TIMEOUT` | `30` | 检查超时（秒） |

```bash
# 示例
OMNIDATA_BROWSER__HEALTH_CHECK_INTERVAL=120
OMNIDATA_BROWSER__HEALTH_CHECK_TIMEOUT=60
```

---

## 完整 .env 示例

```bash
# ================================
# OmniData 配置文件
# ================================

# ----- 浏览器配置 -----
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__CHANNEL=chromium
OMNIDATA_BROWSER__CONTEXT_POOL_MAX_SIZE=10
OMNIDATA_BROWSER__CONTEXT_POOL_IDLE_TIMEOUT=300
OMNIDATA_BROWSER__DEVTOOLS=false

# ----- Redis 配置 -----
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379
OMNIDATA_REDIS__DB=0
OMNIDATA_REDIS__PASSWORD=
OMNIDATA_REDIS__PREFIX=omnidata:
OMNIDATA_REDIS__STATE_TTL=86400

# ----- 数据库配置 -----
OMNIDATA_DB__PATH=omnidata.db
OMNIDATA_AUDIT__RETENTION_DAYS=90

# ----- API 配置 -----
OMNIDATA_API__HOST=0.0.0.0
OMNIDATA_API__PORT=8380
OMNIDATA_API__WORKERS=1

# ----- 爬虫配置 -----
OMNIDATA_SPIDER__RETRY_TIMES=3
OMNIDATA_SPIDER__RETRY_DELAY=1
OMNIDATA_SPIDER__TIMEOUT=30

# ----- MCP 配置 -----
OMNIDATA_MCP__DEFAULT_TRANSPORT=streamable-http
OMNIDATA_MCP__ROUTE_PREFIX=/mcp/
```

---

## 配置验证

启动时验证配置：

```bash
uv run python main.py --validate-config
```

---

## 运行时配置

某些配置支持运行时修改：

```python
from omnidata.core.config import settings

# 读取配置
print(settings.browser.headless)

# 注意：运行时修改不会影响已启动的服务
```

---

## 最佳实践

1. **开发环境**：使用 `.env` 文件
2. **生产环境**：使用系统环境变量或 Secrets 管理
3. **敏感信息**：永远不要提交到 Git
4. **配置验证**：部署前验证配置是否正确
