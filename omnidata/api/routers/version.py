"""
版本检查路由

检测 GitHub 仓库 main 分支的最新提交，供前端比对是否有新版本可升级。
通过 GitHub Atom Feed 获取（无需鉴权、无 API 速率限制），Redis 缓存一小时。
"""

import json
import logging
import xml.etree.ElementTree as ET

import httpx
from fastapi import APIRouter

from omnidata.api.responses import success_response
from omnidata.utils.redis_client import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/version", tags=["version"])

# GitHub 仓库信息
GITHUB_OWNER = "noimank"
GITHUB_REPO = "OmniData"
# commits Atom 订阅源：网页级接口，无需鉴权、无 API 速率限制
ATOM_FEED = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/commits/main.atom"
ATOM_NS = "{http://www.w3.org/2005/Atom}"

# Redis 缓存配置
CACHE_KEY = "omnidata:remote_version"
CACHE_TTL = 3600  # 1 小时，与前端轮询频率对齐


async def _fetch_latest_commit() -> dict:
    """从 GitHub Atom Feed 拉取 main 分支最新提交信息"""
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        resp = await client.get(ATOM_FEED)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)

    # 第一个 entry 即最新提交
    entry = root.find(f"{ATOM_NS}entry")
    if entry is None:
        return {}

    message = (entry.findtext(f"{ATOM_NS}title") or "").strip()
    commit_date = (entry.findtext(f"{ATOM_NS}updated") or "").strip()

    # commit 链接取 rel="alternate" 的 link，其 href 形如 .../commit/<sha>
    html_url = ""
    sha = ""
    for link in entry.findall(f"{ATOM_NS}link"):
        if link.get("rel") == "alternate":
            html_url = link.get("href", "")
            sha = html_url.rsplit("/", 1)[-1]
            break

    return {
        "commit_sha": sha,
        "commit_date": commit_date,
        "message": message,
        "html_url": html_url,
    }


@router.get("/check")
async def check_version():
    """
    检查远端仓库最新版本

    返回 main 分支最新一次提交的信息，前端据此与本地构建版本比对，
    判断是否有新版本可升级。
    """
    redis = await get_redis()

    # 优先读缓存
    cached = await redis.get(CACHE_KEY)
    if cached:
        return success_response(json.loads(cached), "获取成功")

    # 缓存未命中，请求 GitHub；失败时返回空数据，前端静默处理
    try:
        version_info = await _fetch_latest_commit()
    except Exception as e:
        logger.warning(f"Failed to fetch remote version: {e}")
        return success_response({}, "获取成功")

    if version_info:
        await redis.set(CACHE_KEY, json.dumps(version_info), ex=CACHE_TTL)

    return success_response(version_info, "获取成功")
