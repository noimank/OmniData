# 创建爬虫

学习如何开发自己的爬虫。

---

## 爬虫模板

在 `omnidata/data_sources/` 下创建新的爬虫文件：

```python
# omnidata/data_sources/myplatform/spider.py
from pydantic import BaseModel, Field
from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult

class MyParams(BaseModel):
    """请求参数模型"""
    url: str = Field(..., description="目标 URL")
    timeout: int = Field(default=30000, description="超时时间（毫秒）")

class MyPlatformActionSpider(BaseWebSpider):
    """爬虫类"""

    # 基本信息
    name = "myplatform_action"           # 爬虫名称（唯一）
    description = "我的爬虫描述"          # 描述
    version = "1.0.0"                     # 版本
    author = "your_name"                  # 作者
    platform = "我的平台"                 # 平台名称（中文）

    # 参数模型
    params_model = MyParams

    async def crawl(self, params: MyParams) -> SpiderResult:
        """爬虫核心逻辑"""
        async with self.new_page(namespace="my_namespace") as page:
            # 设置超时
            page.set_default_timeout(params.timeout)

            # 访问页面
            await page.goto(params.url)

            # 提取数据
            title = await page.title()

            return SpiderResult(
                success=True,
                data={
                    "title": title,
                    "url": page.url
                }
            )
```

---

## 自动注册

爬虫会被自动发现和注册，无需手动配置！

**扫描规则**：
- 位置：`omnidata/data_sources/**/*.py`
- 基类：继承 `BaseWebSpider`
- 命名：`{Platform}{Action}Spider`

---

## 命名约定

### 爬虫名称

```
{平台}_{动作}
```

| 示例 | 平台 | 动作 |
| :--- | :--- | :--- |
| `eastmoney_stock_quote` | 东方财富 | 股票行情 |
| `sina_global_news` | 新浪 | 全球新闻 |
| `bilibili_video_info` | B站 | 视频信息 |

### 类名

```
{Platform}{Action}Spider
```

| 爬虫名称 | 类名 |
| :--- | :--- |
| `eastmoney_stock_quote` | `EastmoneyStockQuoteSpider` |
| `sina_global_news` | `SinaGlobalNewsSpider` |

---

## 参数定义

### 使用 Pydantic

```python
from pydantic import BaseModel, Field

class StockQuoteParams(BaseModel):
    """股票行情参数"""
    secucode: str = Field(
        ...,
        description="股票代码",
        min_length=6,
        max_length=9
    )
    fields: list[str] = Field(
        default=["name", "price"],
        description="返回字段列表"
    )
```

### 参数验证

```python
# 自动验证
params = StockQuoteParams(
    secucode="000001",    # ✓ 正确
    secucode="123"        # ✗ 验证失败
)
```

---

## 页面操作

### 获取页面

```python
# 方式1：自动管理（推荐）
async with self.new_page(namespace="my_namespace") as page:
    await page.goto("https://example.com")
    # page 会自动关闭

# 方式2：手动管理
context = await self.get_context(namespace="my_namespace")
page = await context.new_page()
try:
    await page.goto("https://example.com")
finally:
    await page.close()
```

### 常用操作

```python
# 导航
await page.goto(url)
await page.go_back()
await page.reload()

# 等待
await page.wait_for_selector(".content")
await page.wait_for_timeout(1000)

# 提取数据
title = await page.title()
text = await page.locator(".content").text_content()
html = await page.locator(".content").inner_html()

# 点击
await page.click(".button")

# 填写表单
await page.fill("#input", "text")

# 截图
screenshot = await page.screenshot()
```

---

## 返回结果

### SpiderResult

```python
from omnidata.core.base_web_spider import SpiderResult

return SpiderResult(
    success=True,                    # 是否成功
    data={...},                      # 返回数据
    metadata={                       # 元数据
        "url": page.url,
        "timestamp": int(time.time())
    }
)
```

### 错误处理

```python
try:
    data = await self._extract_data(page)
    return SpiderResult(success=True, data=data)
except Exception as e:
    return SpiderResult(
        success=False,
        error=str(e)
    )
```

---

## 完整示例

```python
from pydantic import BaseModel, Field
from omnidata.core.base_web_spider import BaseWebSpider, SpiderResult

class EastmoneyStockQuoteParams(BaseModel):
    """东方财富股票行情参数"""
    secucode: str = Field(..., description="股票代码，如 000001")

class EastmoneyStockQuoteSpider(BaseWebSpider):
    """东方财富股票行情爬虫"""
    name = "eastmoney_stock_quote"
    description = "获取股票实时行情"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"
    params_model = EastmoneyStockQuoteParams

    async def crawl(self, params: EastmoneyStockQuoteParams) -> SpiderResult:
        """获取股票行情"""
        url = f"http://push2.eastmoney.com/api/qt/stock/get"
        async with self.new_page(namespace="eastmoney") as page:
            response = await page.goto(
                url,
                params={"secid": f"1.{params.secucode}"}
            )

            data = await response.json()

            if data and "data" in data:
                return SpiderResult(
                    success=True,
                    data={
                        "name": data["data"]["name"],
                        "price": data["data"]["f60"],
                        "change": data["data"]["f169"]
                    }
                )

            return SpiderResult(
                success=False,
                error="获取数据失败"
            )
```

---

## 测试爬虫

```bash
# 命令行测试
uv run python main.py --run eastmoney_stock_quote --secucode 000001

# API 测试
curl -X POST http://localhost:8380/spiders/run \
  -H "Content-Type: application/json" \
  -d '{
    "spider_name": "eastmoney_stock_quote",
    "params": {"secucode": "000001"}
  }'
```

---

## 最佳实践

1. **参数验证**：使用 Pydantic 定义严格参数规则
2. **命名空间**：为不同用途使用不同 namespace
3. **错误处理**：捕获并处理预期异常
4. **元数据**：返回调试信息
5. **幂等性**：相同参数返回相同结果

---

## 下一步

- [添加登录](adding-login.md) - 处理需要登录的网站
- [测试指南](testing.md) - 编写测试用例
