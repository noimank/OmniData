"""
东方财富 push2 / push2his 接口统一请求客户端

通过浏览器上下文 (page.context.request.get) 走真实浏览器请求路径，
附带指数退避重试，规避 page.evaluate(fetch()) 的 CORS / 网络抖动风险。
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_MS = 15000
MAX_RETRIES = 3


async def fetch_with_retry(
    page,
    url: str,
    params: dict,
    *,
    referer: str,
    response_type: str = "text",
    max_retries: int = MAX_RETRIES,
) -> Any:
    """
    通过浏览器上下文请求 push2/push2his 接口，含指数退避重试

    避免在 page.evaluate(fetch()) 中因 CORS 偶发失败 / 网络抖动返回 None。
    非 2xx 状态或抛异常时按 1s/2s/4s 退避重试，最终仍失败返回 None。

    Args:
        page: Playwright Page 对象，使用其 context.request 走真实浏览器请求
        url: 目标 API URL
        params: URL 查询参数
        referer: Referer 请求头
        response_type: "text" 返回原始字符串（JSONP / JSON），"json" 自动反序列化
        max_retries: 最大重试次数

    Returns:
        成功返回 response_type 对应类型的响应体；最终失败返回 None
    """
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = await page.context.request.get(
                url,
                params=params,
                headers={"Referer": referer},
                timeout=REQUEST_TIMEOUT_MS,
            )
            if response.status == 200:
                if response_type == "json":
                    return await response.json()
                return await response.text()
        except Exception as e:  # 网络抖动、握手失败等
            last_error = e

        if attempt < max_retries - 1:
            await asyncio.sleep(2**attempt)

    if last_error is not None:
        logger.warning("push2 fetch failed after %d retries (%s): %s", max_retries, url, last_error)
    return None


async def warmup_push2(page, fallback_url: str | None = None) -> None:
    """
    暖手 push2 域：先访问 push2 域相关页面建立 cookies，再回到原页面

    push2.eastmoney.com 接口依赖浏览器在 quote.eastmoney.com 域上持有的 cookies，
    首次直接请求 push2 接口可能因缺少 cookies 返回 403 / 异常。

    Args:
        page: Playwright Page 对象
        fallback_url: 暖手后回到的页面（通常是入口页），无则不回
    """
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    try:
        await page.goto("https://quote.eastmoney.com/center/gridlist.html")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        if fallback_url:
            await page.goto(fallback_url)
    except Exception:
        pass
