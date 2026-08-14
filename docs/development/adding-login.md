# 添加登录

为需要登录的网站添加二维码登录支持。

---

## 登录基类

继承 `BaseQRLogin` 创建登录模块：

```python
# omnidata/data_sources/myplatform/login.py
from omnidata.core import BaseQRLogin, QRLoginState, QRCode

class MyPlatformQRLogin(BaseQRLogin):
    """我的平台二维码登录"""

    # 基本信息（name 就是浏览器 context 的命名空间，注意了）
    name = "myplatform"
    description = "我的平台登录"
    version = "1.0.0"
    author = "your_name"
    platform = "我的平台"
```

放在 `omnidata/data_sources/{platform}/login.py` 下即会被自动发现，无需手动注册。

---

## 必须实现的抽象方法

`BaseQRLogin` 定义了以下**必须实现**的抽象方法：

### 1. `refresh_login_state()` → None

定期刷新登录状态到 Redis（由登录注册器后台任务调用）。

```python
async def refresh_login_state(self) -> None:
    """重新保存登录状态到 Redis"""
    context = await self.browser_context_pool.get_context("myplatform")
    page = await context.new_page()
    try:
        login_state = await self.is_login()
        if login_state.status == "success":
            await self.save_context_state(context, "myplatform")
    finally:
        await page.close()
```

### 2. `get_qrcode_types()` → list

返回支持的二维码类型。

```python
async def get_qrcode_types(self) -> list:
    return ["扫码登录"]
```

### 3. `get_qrcode(qr_type: str)` → QRCode

获取指定类型的二维码。**使用 `self._qr_page` 和 `self._qr_context`** 进行操作，通常按 `qr_type` 分发到不同的获取逻辑。

```python
async def get_qrcode(self, qr_type: str = "扫码登录") -> QRCode:
    # 建立专用 context 和 page（与 verify_login_state 共用）
    self._qr_context = await self.browser_context_pool.get_context("myplatform")
    self._qr_page = await self._qr_context.new_page()
    try:
        await self.apply_anti_detection_scripts(self._qr_page, "advanced")
        await self._qr_page.goto("https://example.com/login")

        # 截取二维码图片（返回 Base64 Data URI，避免二次访问导致二维码变化）
        qr_code_base64 = await self.screenshot_element_to_base64(
            self._qr_page, ".qrcode img"
        )

        return QRCode(
            url=qr_code_base64,
            qr_type=qr_type,
            success=True,
            message="获取二维码成功",
        )
    except Exception as e:
        await self.close()  # 出错就关闭，防止资源泄露
        return QRCode(url="", qr_type=qr_type, success=False, message=str(e))
```

### 4. `verify_login_state()` → QRLoginState

验证二维码登录是否完成。**与 `get_qrcode` 共用 `self._qr_page` 和 `self._qr_context`**。

```python
async def verify_login_state(self) -> QRLoginState:
    """验证登录状态（轮询接口）"""
    if not self._qr_page_alive():
        return QRLoginState(status="failed", message="QR code page not initialized")

    try:
        # 检查登录是否成功
        await self._qr_page.locator(".user-info").wait_for(timeout=5000)

        # 登录成功：保存登录状态到 Redis，关闭专用页面
        await self.save_context_state(self._qr_context, "myplatform")
        await self.close()
        return QRLoginState(status="success", message="登录成功")
    except Exception:
        return QRLoginState(status="waiting", message="等待扫码登录中......")
```

### 5. `is_login()` → QRLoginState

验证当前是否已登录。**使用独立的 page/context**（通过 `self.new_page(namespace)` 获取），与扫码会话分离。

```python
async def is_login(self) -> QRLoginState:
    """验证是否已登录"""
    try:
        async with self.new_page("myplatform") as page:
            await page.goto("https://example.com/account")
            if "login" in page.url:
                return QRLoginState(status="not_logged_in", message="未登录")

            await page.locator(".user-info").wait_for(timeout=5000)
            return QRLoginState(status="success", message="已登录")
    except Exception:
        return QRLoginState(status="not_logged_in", message="未登录")
```

---

## 数据结构

### QRCode

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `success` | `bool` | 是否成功获取二维码 |
| `url` | `str` | 二维码资源地址（通常是 Base64 Data URI） |
| `qr_type` | `str` | 二维码登录类型 |
| `message` | `str` | 描述信息 |

### QRLoginState

`status` 取值范围：`waiting` / `success` / `failed` / `not_logged_in`。

---

## 常用辅助方法

| 方法 | 说明 |
| :--- | :--- |
| `screenshot_element_to_base64(page, selector)` | 截取页面元素并转换为 Base64 Data URI（保证二维码一致性） |
| `save_context_state(context, namespace)` | 保存登录状态到 Redis（无 TTL） |
| `set_login_status(status)` / `get_login_status()` | 读写登录状态缓存 |
| `close()` | 清理二维码会话资源（幂等，可安全重复调用） |
| `has_active_qr_session()` | 是否存在进行中的二维码登录会话 |

---

## API 使用

### 列出登录器

```bash
curl http://localhost:8380/api/v1/logins
```

### 获取二维码

```bash
curl -X POST http://localhost:8380/api/v1/logins/bilibili/qrcode \
  -H "Content-Type: application/json" \
  -d '{"qr_type": "扫码登录"}'
```

```json
{
  "success": true,
  "message": "获取扫码登录 二维码成功",
  "data": {
    "login_name": "bilibili",
    "url": "data:image/png;base64,iVBORw0KGgo...",
    "qr_type": "扫码登录"
  }
}
```

### 轮询验证登录

```bash
curl -X POST http://localhost:8380/api/v1/logins/bilibili/verify
```

### 检查登录状态

```bash
curl http://localhost:8380/api/v1/logins/bilibili/status
```

```json
{
  "success": true,
  "message": "获取登录状态成功",
  "data": {
    "status": "success",
    "message": "登录成功"
  }
}
```

### 清除登录态

```bash
curl -X DELETE http://localhost:8380/api/v1/logins/bilibili/session
```

### 清理二维码资源

```bash
curl -X POST http://localhost:8380/api/v1/logins/bilibili/cleanup
```

---

## 在爬虫中使用登录态

登录态以 `login.name` 作为命名空间持久化到 Redis。爬虫使用**相同的命名空间**即可自动复用：

```python
class MySpider(BaseWebSpider):
    async def crawl(self, params: MyParams) -> SpiderResult:
        # 使用与登录器 name 相同的命名空间，自动恢复登录态
        async with self.new_page(namespace="myplatform") as page:
            await page.goto("https://example.com/user")
            user_info = await page.locator(".user-info").text_content()
            return SpiderResult(success=True, data={"user": user_info})
```

---

## 最佳实践

1. **name 即命名空间**：`name` 属性就是浏览器 context 的命名空间，与爬虫复用登录态时需保持一致
2. **截图保证一致性**：用 `screenshot_element_to_base64` 截取二维码，避免二次访问导致二维码变化
3. **错误时关闭资源**：`get_qrcode` 出错时调用 `close()`，防止 `_qr_page` 泄露
4. **登录成功后保存**：`verify_login_state` 确认成功后调用 `save_context_state` 持久化登录态
5. **is_login 独立上下文**：状态检查使用 `self.new_page(namespace)`，避免干扰扫码会话

---

## 下一步

- [创建爬虫](creating-spider.md) - 创建使用登录态的爬虫
- [部署指南](deployment.md) - 部署到生产环境
