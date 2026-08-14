"""
东方财富批量实时行情 Spider
一次请求获取多只证券（股票 / 指数 / ETF / 可转债等）的实时行情报价

通过 push2.eastmoney.com 的 ulist.np/get 接口批量查询（secids 逗号分隔），
字段语义与单只的 stock/get 接口不同（ulist 中 f2=最新价、f3=涨跌幅、f12=代码、f14=名称）。
单次请求实测可携带 300+ 只证券，为避免 URL 过长与偶发限流，内部按批次（默认 100）顺序请求。

注意：ulist 批量接口不提供买卖五档数据（该能力仅在单只 stock/get 接口可用）。
"""

import random
import re
from datetime import datetime

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult
from omnidata.data_sources.eastmoney._push2_client import fetch_with_retry


class RealtimeQuoteParams(BaseModel):
    """批量实时行情参数模型"""

    secids: str = Field(
        ...,
        min_length=1,
        max_length=20000,
        description=(
            "证券标识，逗号分隔，每项支持两种格式："
            "① 完整 secid（market.code），如 '1.600519'(贵州茅台)、'1.000001'(上证指数)、'0.920002'(北交所)；"
            "② 裸 6 位代码自动推断市场，如 '600519'、'000001'、'300750'、'510050'。"
            "注意：'000001' 等代码存在歧义（平安银行 vs 上证指数），自动推断按股票处理，指数请显式传 '1.000001'"
        ),
    )


class RealtimeQuoteSpider(BaseWebSpider):
    """
    东方财富批量实时行情 Spider

    一次请求获取多只证券的实时行情报价，支持股票、指数、ETF、可转债等。
    返回每只证券的最新价、涨跌幅、涨跌额、成交量、成交额、振幅、换手率、量比、
    市盈率、市净率、总市值、流通市值、最高、最低、今开、昨收、所属行业、更新时间等。
    自动分批请求，超过单批上限的证券会按顺序分批拉取后合并。
    """

    name = "eastmoney_realtime_quote"
    description = "批量获取多只股票/指数/ETF实时行情报价，包括最新价、涨跌幅、成交量、成交额、振幅、换手率、量比、市盈率、市净率、总市值等完整行情数据，支持自动分批"
    version = "1.1.0"
    author = "noimank"
    platform = "东方财富"

    params_model = RealtimeQuoteParams

    # API 配置 - 使用 ulist.np/get 接口批量查询
    API_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    DEFAULT_UT = "b2884a393a59ad64002292a3e90d46a5"
    # 请求字段（ulist 字段语义，fltt=2 时直接返回小数价格）
    FIELDS = (
        "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,"
        "f20,f21,f22,f23,f24,f25,f100,f115,f124"
    )
    # 单批请求的证券数量上限（实测 300+ 可一次返回，留足余量）
    CHUNK_SIZE = 100

    async def crawl(self, params: RealtimeQuoteParams) -> SpiderResult:
        """
        爬取批量实时行情数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        # 规范化证券标识为 secid（market.code），去重并保留顺序
        identifiers = [s for s in params.secids.split(",") if s.strip()]
        secids, skipped = self._normalize_secids(identifiers)
        if not secids:
            return SpiderResult(
                success=False,
                message=f"没有有效的证券标识，请检查参数格式（应为 6 位代码或 market.code）",
            )

        async with self.new_page("eastmoney") as page:
            await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

            # ── 动态提取 ut 令牌：拦截入口页面加载时自身发起的 push2 API 请求 ──
            captured_ut = {}

            async def capture_ut(route):
                m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                if m:
                    captured_ut["token"] = m.group(1)
                await route.continue_()

            await page.route("**push2.eastmoney.com**", capture_ut)

            await page.goto("https://quote.eastmoney.com/center/gridlist.html")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except PlaywrightTimeoutError:
                # DOMContentLoaded 超时不影响后续流程：ut 拿不到时会回退到 DEFAULT_UT
                pass

            ut = captured_ut.get("token") or self.DEFAULT_UT

            # ── 分批请求并合并结果 ──
            quotes: list[dict] = []
            for i in range(0, len(secids), self.CHUNK_SIZE):
                chunk = secids[i : i + self.CHUNK_SIZE]
                result = await fetch_with_retry(
                    page,
                    self.API_URL,
                    {
                        "fltt": "2",
                        "invt": "2",
                        "fields": self.FIELDS,
                        "secids": ",".join(chunk),
                        "ut": ut,
                        "_": str(random.randint(10**12, 10**13 - 1)),
                    },
                    response_type="json",
                )

                if result is None:
                    return SpiderResult(
                        success=False,
                        message=f"请求失败（第{len(quotes) // self.CHUNK_SIZE + 1}批）",
                    )

                if result.get("rc") != 0:
                    return SpiderResult(
                        success=False, message=f"获取数据失败：{result.get('msg', '未知错误')}"
                    )

                diff = (result.get("data") or {}).get("diff") or []
                quotes.extend(self._parse_quote_item(item) for item in diff)

            if not quotes:
                return SpiderResult(
                    success=False,
                    message="未匹配到任何证券数据，请检查证券标识是否正确",
                )

            message = f"成功获取 {len(quotes)} 只证券的实时行情"
            if skipped:
                message += f"（跳过 {len(skipped)} 个无效标识：{', '.join(skipped)}）"

            return SpiderResult(
                success=True,
                data={
                    "total": len(quotes),
                    "quotes": quotes,
                    "skipped": skipped,
                },
                message=message,
            )

    @staticmethod
    def _normalize_secids(identifiers: list[str]) -> tuple[list[str], list[str]]:
        """
        将证券标识列表规范化为 secid（market.code），去重并保留顺序

        - 完整 secid（含点）直接保留，如 "1.600519"
        - 裸 6 位代码按前缀推断市场：
            92 开头 → 北交所(0)；6/5/9 开头 → 沪市(1)；其余 → 深市(0)

        Args:
            identifiers: 用户传入的证券标识列表

        Returns:
            (有效 secid 列表, 被跳过的无效标识列表)
        """
        secids: list[str] = []
        skipped: list[str] = []
        seen: set[str] = set()
        for identifier in identifiers:
            identifier = identifier.strip()
            if "." in identifier:
                if re.fullmatch(r"\d+\.\d{6}", identifier):
                    candidate = identifier
                else:
                    skipped.append(identifier)
                    continue
            else:
                if not re.fullmatch(r"\d{6}", identifier):
                    skipped.append(identifier)
                    continue
                code = identifier
                if code.startswith("92"):
                    candidate = f"0.{code}"  # 北交所新代码段 920xxx
                elif code.startswith(("6", "5", "9")):
                    candidate = f"1.{code}"  # 沪市：主板/科创板/ETF/B股
                else:
                    candidate = f"0.{code}"  # 深市/北交所：000/001/002/003/300/301/159/4xx/8xx
            if candidate not in seen:
                seen.add(candidate)
                secids.append(candidate)
        return secids, skipped

    @staticmethod
    def _parse_quote_item(item: dict) -> dict:
        """
        解析单条行情数据（ulist 字段语义）

        Args:
            item: API 返回的单条数据

        Returns:
            解析后的数据字典
        """

        def to_float(value):
            """安全转换为 float，'-' 或无值返回 None（避免把无行情误标为 0）"""
            if value is None or value == "" or value == "-":
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        def to_int(value):
            """安全转换为 int，'-' 或无值返回 None"""
            if value is None or value == "" or value == "-":
                return None
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return None

        code = str(item.get("f12") or "")
        market_id = int(item.get("f13") or 0)
        if market_id == 1:
            market = "沪市"
        elif code.startswith(("4", "8", "92")):
            market = "北交所"
        else:
            market = "深市"

        # 更新时间戳
        timestamp = to_int(item.get("f124"))
        update_time = (
            datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp else ""
        )

        return {
            "证券代码": code,
            "证券名称": str(item.get("f14") or ""),
            "市场": market,
            "最新价": to_float(item.get("f2")),
            "涨跌幅(%)": to_float(item.get("f3")),
            "涨跌额": to_float(item.get("f4")),
            "成交量(手)": to_int(item.get("f5")),
            "成交额(元)": to_float(item.get("f6")),
            "振幅(%)": to_float(item.get("f7")),
            "换手率(%)": to_float(item.get("f8")),
            "量比": to_float(item.get("f10")),
            "市盈率(动态)": to_float(item.get("f9")),
            "市盈率(TTM)": to_float(item.get("f115")),
            "市净率": to_float(item.get("f23")),
            "最高": to_float(item.get("f15")),
            "最低": to_float(item.get("f16")),
            "今开": to_float(item.get("f17")),
            "昨收": to_float(item.get("f18")),
            "总市值(元)": to_float(item.get("f20")),
            "流通市值(元)": to_float(item.get("f21")),
            "涨速": to_float(item.get("f22")),
            "60日涨跌幅(%)": to_float(item.get("f24")),
            "年初至今涨跌幅(%)": to_float(item.get("f25")),
            "所属行业": (
                str(item.get("f100") or "") if item.get("f100") not in (None, "", "-") else ""
            ),
            "更新时间": update_time,
        }
