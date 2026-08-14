# 配置参考

OmniData 的完整配置说明。

---

## 配置方式

OmniData 使用 `pydantic-settings` 管理配置，支持：

- **环境变量**：优先级最高
- **.env 文件**：开发环境推荐（`main.py` 启动时自动加载）
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

## 应用配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_APP_NAME` | `OmniData` | 应用名称 |
| `OMNIDATA_APP_VERSION` | `0.1.0` | 应用版本 |
| `OMNIDATA_DEBUG` | `false` | 调试模式 |

---

## 浏览器配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_BROWSER__HEADLESS` | `true` | 无头模式 |
| `OMNIDATA_BROWSER__DEFAULT_TIMEOUT` | `8000` | Playwright 操作超时（毫秒） |
| `OMNIDATA_BROWSER__ARGS` | 见代码 | 浏览器启动参数（反爬虫优化） |
| `OMNIDATA_BROWSER__IGNORE_DEFAULT_ARGS` | 见代码 | 需忽略的默认启动参数 |

!!! note "浏览器稳定机制不对外配置"
    Context 池化复用、空闲回收、浏览器整体回收、自愈策略等均为内核内置固定策略
    （见 `BrowserContextPool` 类常量），自动运行，**不提供环境变量**，避免误调。

```bash
# 示例
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__DEFAULT_TIMEOUT=10000
```

---

## Redis 配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_REDIS__HOST` | `localhost` | Redis 主机 |
| `OMNIDATA_REDIS__PORT` | `6379` | Redis 端口 |
| `OMNIDATA_REDIS__DB` | `0` | Redis 数据库编号 |
| `OMNIDATA_REDIS__PASSWORD` | `null` | Redis 密码 |
| `OMNIDATA_REDIS__MAX_CONNECTIONS` | `10` | 连接池最大连接数 |

```bash
# 示例
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379
OMNIDATA_REDIS__PASSWORD=your_password
OMNIDATA_REDIS__MAX_CONNECTIONS=20
```

---

## 登录器配置

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OMNIDATA_LOGIN__CHECK_CONCURRENCY` | `5` | 登录状态检查的最大并发数 |
| `OMNIDATA_LOGIN__CHECK_TIMEOUT` | `30` | 单次检查的超时时间（秒） |

```bash
# 示例
OMNIDATA_LOGIN__CHECK_CONCURRENCY=10
OMNIDATA_LOGIN__CHECK_TIMEOUT=60
```

---

## 完整 .env 示例

参考项目根目录的 `.env.example`：

```bash
# 应用配置
OMNIDATA_APP_NAME=OmniData
OMNIDATA_APP_VERSION=0.1.0
OMNIDATA_DEBUG=false

# 浏览器配置
OMNIDATA_BROWSER__HEADLESS=true
OMNIDATA_BROWSER__DEFAULT_TIMEOUT=8000

# Redis 配置
OMNIDATA_REDIS__HOST=localhost
OMNIDATA_REDIS__PORT=6379
OMNIDATA_REDIS__DB=0
OMNIDATA_REDIS__PASSWORD=your_password
OMNIDATA_REDIS__MAX_CONNECTIONS=10

# 登录器配置
OMNIDATA_LOGIN__CHECK_CONCURRENCY=5
OMNIDATA_LOGIN__CHECK_TIMEOUT=30
```

---

## 配置读取

```python
from omnidata.core.config import settings

# 读取配置
print(settings.browser.headless)
print(settings.redis.host)
print(settings.login.check_concurrency)
```

---

## 最佳实践

1. **开发环境**：使用 `.env` 文件
2. **生产环境**：使用系统环境变量或 Secrets 管理
3. **敏感信息**：永远不要提交到 Git
