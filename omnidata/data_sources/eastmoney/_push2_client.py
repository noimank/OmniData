"""
东方财富 push2 / push2his 接口统一请求客户端

在东财页面上通过 page.evaluate(fetch()) 发请求，走 Chromium 完整网络栈，
TLS / HTTP2 / 请求头 / cookie 与真实前端 XHR 一致；page.request 走 Node
驱动侧 HTTP 客户端，指纹与浏览器不符，不采用。附带指数退避重试，
应对网络抖动与风控偶发拦截。
"""

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_MS = 15000
MAX_RETRIES = 3

# credentials: push2 的 Access-Control-Allow-Origin 回显东财各子域 origin
# 且 Allow-Credentials: true，携带 cookie 的跨域 fetch 可通过
FETCH_JS = """
async ([url, params, timeoutMs]) => {
    const u = new URL(url);
    for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
    const resp = await fetch(u.toString(), {
        credentials: 'include',
        signal: AbortSignal.timeout(timeoutMs),
    });
    return { status: resp.status, body: await resp.text() };
}
"""


async def fetch_with_retry(
    page,
    url: str,
    params: dict,
    *,
    response_type: str = "text",
) -> Any:
    """
    在东财页面内 fetch push2/push2his 接口，含指数退避重试

    前置条件：调用时页面须已停留在东财域页面上——fetch 的 origin / Referer /
    cookies 由该页面提供（各爬虫为捕获 ut 本就先 goto 东财入口页）。
    网络 / CORS / 非 2xx / 解析失败按 1s/2s/4s 退避重试，最终仍失败返回 None。

    Args:
        page: Playwright Page 对象（当前须停留在东财域页面上）
        url: 目标 API URL
        params: URL 查询参数
        response_type: "text" 返回原始字符串（JSONP / JSON），"json" 自动反序列化

    Returns:
        成功返回 response_type 对应类型的响应体；最终失败返回 None
    """
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            result = await page.evaluate(FETCH_JS, [url, params, REQUEST_TIMEOUT_MS])
            if result["status"] == 200:
                if response_type == "json":
                    return json.loads(result["body"])
                return result["body"]
            last_error = RuntimeError(f"HTTP {result['status']}")
        except Exception as e:  # 网络抖动、CORS、风控拦截、页面导航等
            last_error = e

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2**attempt)

    logger.warning("push2 fetch failed after %d retries (%s): %s", MAX_RETRIES, url, last_error)
    return None
