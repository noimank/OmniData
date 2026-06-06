"""
同花顺 A股市场涨跌分布 Spider
从 https://q.10jqka.com.cn/ 获取A股市场涨跌分布概览数据

原理：
    1. 导航到 q.10jqka.com.cn 页面，获取 Chameleon 反爬 cookie/session
    2. 等待 JS 渲染完成
    3. 在同一 browser context 内调用 api.php?t=indexflash&type=all 获取 JSON 数据
    4. 解析 JSON 返回结构化市场概况

API: GET api.php?t=indexflash&type=all  (JSON)

返回字段说明：
	    zdfb_data.zdfb: 涨跌分布10区间（含精确百分比边界），区间依次为：
	        [-∞, -8%]   [-8%, -6%]   [-6%, -4%]   [-4%, -2%]   [-2%, 0)
	        [0, 2%]     (2%, 4%]     (4%, 6%]     (6%, 8%]     [8%, +∞]
    zdfb_data.znum: 上涨总只数
    zdfb_data.dnum: 下跌总只数
    zdt_data: 涨跌停分时数据
    jrbx_data: 昨日涨停今日表现
    dppj_data: 大盘评级

反爬说明：
    同花顺 Nginx WAF 会拦截没有 session token 的直接 API 请求。
    必须先通过 page.goto() 导航页面获取 Chameleon cookie，再在同一 context 内调用 API。
"""

import asyncio
import json
import logging
from typing import Any

from pydantic import BaseModel

from omnidata.core import BaseWebSpider, SpiderResult

logger = logging.getLogger(__name__)


# ============================================================================
# 参数模型
# ============================================================================


class MarketOverviewParams(BaseModel):
    """同花顺 A股市场涨跌分布参数模型（无必填参数，默认获取全市场数据）"""

    pass


# ============================================================================
# Spider 主体
# ============================================================================


class MarketOverviewSpider(BaseWebSpider):
    """
    同花顺 A股市场涨跌分布 Spider

    返回 A 股全市场涨跌分布概览数据，包括：
    - 10区间涨跌分布（页面柱状图：跌停/-8%/-6%/-4%/-2%/0/2%/4%/6%/8%/涨停）
    - 涨跌停统计及分时趋势
    - 大盘评级与昨日涨停表现
    - 涨幅前20名股票
    - 主要指数行情

    数据来源: https://q.10jqka.com.cn/
    API: api.php?t=indexflash&type=all
    """

    name = "ths_10jqka_market_overview"
    description = "获取同花顺A股市场涨跌分布概览数据（10区间分布、涨跌停、大盘评级）"
    version = "3.0.0"
    author = "noimank"
    platform = "同花顺10jqka"

    params_model = MarketOverviewParams

    PAGE_URL = "https://q.10jqka.com.cn/"
    INDEXFLASH_API = "https://q.10jqka.com.cn/api.php?t=indexflash&type=all"

    # 涨跌分布10区间（由页面图表坐标轴刻度确定：跌停 -8% -6% -4% -2% 0 2% 4% 6% 8% 涨停）
    ZDFB_LABELS = [
        "[-∞, -8%]",
        "[-8%, -6%]",
        "[-6%, -4%]",
        "[-4%, -2%]",
        "[-2%, 0)",
        "[0, 2%]",
        "(2%, 4%]",
        "(4%, 6%]",
        "(6%, 8%]",
        "[8%, +∞]",
    ]

    async def crawl(self, params: MarketOverviewParams) -> SpiderResult:
        """
        加载页面 → 调用 indexflash API → 解析返回

        流程：
        1. 导航到 q.10jqka.com.cn（获取 cookie/session）
        2. 等待页面 JS 渲染完成
        3. 在同 context 内调用 api.php?t=indexflash 获取 JSON
        4. 解析并构建结构化结果
        """
        try:
            async with self.new_page("ths_10jqka") as page:
                # 加载页面获取 cookie / session
                logger.info("加载同花顺行情中心页面...")
                await page.goto(
                    self.PAGE_URL,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await asyncio.sleep(3)  # 等待 Chameleon 反爬脚本和 JS 渲染

                # 调用 indexflash JSON API
                logger.info("请求 indexflash API...")
                response = await page.request.get(self.INDEXFLASH_API, timeout=15000)

                if response.status != 200:
                    return SpiderResult(
                        success=False,
                        message=f"API 请求失败：HTTP {response.status}",
                    )

                body_text = await response.text()
                if not body_text or len(body_text) < 10:
                    return SpiderResult(
                        success=False,
                        message="API 返回空数据",
                    )

                try:
                    data = json.loads(body_text)
                except json.JSONDecodeError:
                    return SpiderResult(
                        success=False,
                        message=f"API 返回非 JSON 数据: {body_text[:200]}",
                    )

                # 解析数据
                result_data = self._parse(data)

                overview = result_data["市场概况"]
                return SpiderResult(
                    success=True,
                    data=result_data,
                    message=(
                        f"A股市场概况：上涨{overview['上涨家数']}只 "
                        f"({overview['上涨比例']}%)，"
                        f"下跌{overview['下跌家数']}只 "
                        f"({overview['下跌比例']}%)，"
                        f"涨停{overview['涨停家数']}只，"
                        f"跌停{overview['跌停家数']}只，"
                        f"大盘评级{overview.get('大盘评级', 'N/A')}分"
                    ),
                )

        except Exception as e:
            logger.exception(f"爬取失败：{e}")
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    # ------------------------------------------------------------------
    # 数据解析
    # ------------------------------------------------------------------

    def _parse(self, data: dict) -> dict[str, Any]:
        """解析 indexflash API 返回的 JSON 数据"""

        zdfb_data = data.get("zdfb_data", {})
        zdt_data = data.get("zdt_data", {})
        jrbx_data = data.get("jrbx_data", {})
        dppj = data.get("dppj_data")

        # ── 涨跌分布 ──
        zdfb_raw = zdfb_data.get("zdfb", [])
        znum = zdfb_data.get("znum", 0)
        dnum = zdfb_data.get("dnum", 0)

        distribution = []
        for i, count in enumerate(zdfb_raw):
            distribution.append({
                "区间": self.ZDFB_LABELS[i] if i < len(self.ZDFB_LABELS) else f"区间{i}",
                "数量": count,
            })

        # ── 涨跌停 ──
        last_zdt = zdt_data.get("last_zdt", {})

        # ── 涨跌停分时趋势（采样约20个点） ──
        timeline = []
        zd_time = zdt_data.get("zd_time", [])
        ztzs = zdt_data.get("ztzs", [])
        dtzs = zdt_data.get("dtzs", [])
        step = max(1, len(zd_time) // 20) if zd_time else 1
        for i in range(0, len(zd_time), step):
            timeline.append({
                "时间": zd_time[i],
                "涨停": ztzs[i] if i < len(ztzs) else 0,
                "跌停": dtzs[i] if i < len(dtzs) else 0,
            })

        return {
            "涨跌分布": distribution,
            "上涨总数": znum,
            "下跌总数": dnum,
            "市场概况": {
                "上涨家数": znum,
                "下跌家数": dnum,
                "涨停家数": last_zdt.get("ztzs", 0),
                "跌停家数": last_zdt.get("dtzs", 0),
                "上涨比例": round(znum / (znum + dnum) * 100, 2) if (znum + dnum) else 0,
                "下跌比例": round(dnum / (znum + dnum) * 100, 2) if (znum + dnum) else 0,
                "昨日涨停今日表现": jrbx_data.get("last_zdf"),
                "大盘评级": dppj,
            },
            "涨跌停分时走势": timeline,
            "涨跌停分时明细": {
                "时间序列": zd_time,
                "涨停序列": ztzs,
                "跌停序列": dtzs,
                "当前涨停": last_zdt.get("ztzs", 0),
                "当前跌停": last_zdt.get("dtzs", 0),
            },
            "大盘评级": dppj,
        }
