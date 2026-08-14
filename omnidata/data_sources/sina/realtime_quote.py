"""
新浪财经批量实时行情 Spider
一次请求获取多只证券（股票 / 指数 / ETF 等）的实时行情报价

通过 hq.sinajs.cn 的 list 接口批量查询（symbols 逗号分隔），经浏览器上下文
（page.request）发起请求：共享上下文 cookie、自动携带真实 Chrome UA，请求前
先访问新浪财经首页以拟人化访问链路（真实用户先浏览首页再拉行情）。
免登录、免 API Key，接口门槛仅为新浪财经域 Referer 头。
单次请求实测可携带 200+ 只证券，为避免 URL 过长，内部按批次（默认 200）顺序请求。

股票 / ETF / 指数返回相同字段布局：
    名称,今开,昨收,最新,最高,最低,买一价,卖一价,成交量,成交额,
    买一量,买一价,...,买五量,买五价,卖一量,卖一价,...,卖五量,卖五价,日期,时间,状态
指数（sh000xxx / sz399xxx）无盘口，买一卖一及五档均为 0。
成交量单位：股票 / ETF / 深证系列指数为股，上证系列指数（sh000xxx）为手。
"""

import asyncio
import logging
import re

from playwright.async_api import Page
from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult

logger = logging.getLogger(__name__)


class RealtimeQuoteParams(BaseModel):
    """批量实时行情参数模型"""

    symbols: str = Field(
        ...,
        min_length=1,
        max_length=20000,
        description=(
            "证券标识，逗号分隔，每项支持两种格式："
            "① 新浪前缀格式，如 'sh600519'(贵州茅台)、'sz000001'(平安银行)、'bj920000'(北交所)；"
            "② 裸 6 位代码自动推断市场：92/8/4 开头→北交所，6/5/9 开头→沪市，其余→深市。"
            "注意：'000001' 存在歧义（平安银行 vs 上证指数），裸代码按股票处理，指数请显式传 'sh000001'"
        ),
    )


class RealtimeQuoteSpider(BaseWebSpider):
    """
    新浪财经批量实时行情 Spider

    一次请求获取多只证券的实时行情报价，支持股票、指数、ETF 等。
    返回每只证券的最新价、涨跌额、涨跌幅、今开昨收、最高最低、振幅、成交量、成交额、
    买卖五档盘口、更新时间等。自动分批请求，超过单批上限的证券会按顺序分批拉取后合并。
    经浏览器上下文（page.request）发起请求：共享上下文 cookie、自动携带真实 Chrome UA，
    请求前暖手访问首页以拟人化访问链路；接口门槛仅为新浪财经域 Referer。免登录、免 API Key。
    """

    name = "sina_realtime_quote"
    description = "批量获取多只股票/指数/ETF实时行情报价，包括最新价、涨跌额、涨跌幅、成交量、成交额、振幅、买卖五档盘口等，免登录免Key，浏览器请求自动分批"
    version = "1.0.0"
    author = "noimank"
    platform = "新浪财经"

    params_model = RealtimeQuoteParams

    # API 配置 - 新浪财经实时行情批量接口
    API_URL = "https://hq.sinajs.cn/list"
    # 接口要求携带新浪财经域 Referer，否则返回 Forbidden
    REFERER = "https://finance.sina.com.cn/"
    # 暖手访问的新浪财经入口页，拟人化访问链路并累积 sina 域 cookie
    ENTRY_URL = "https://finance.sina.com.cn/"
    # 单批请求的证券数量上限（实测 200 只可一次返回）
    CHUNK_SIZE = 200
    # 单次请求超时（毫秒）
    REQUEST_TIMEOUT_MS = 15000
    # 入口页加载超时（毫秒）
    PAGE_TIMEOUT_MS = 15000
    # 请求失败时的最大重试次数（指数退避 1s/2s/4s）
    MAX_RETRIES = 3
    # 行情行正则：var hq_str_sh600519="...";
    LINE_RE = re.compile(r'var hq_str_([a-z]{2}\d{6})="(.*)";')
    # 指数符号模式（上证指数 sh000xxx / 深证指数 sz399xxx）
    INDEX_RE = re.compile(r"(?:sh000|sz399)\d{3}")

    async def crawl(self, params: RealtimeQuoteParams) -> SpiderResult:
        """
        爬取批量实时行情数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        # 规范化证券标识为新浪符号（sh600519），去重并保留顺序
        identifiers = [s for s in params.symbols.split(",") if s.strip()]
        symbols, skipped = self._normalize_symbols(identifiers)
        if not symbols:
            return SpiderResult(
                success=False,
                message="没有有效的证券标识，请检查参数格式（应为 sh600519/sz000001 或 6 位代码）",
            )

        quotes: list[dict] = []
        no_data: list[str] = []
        async with self.new_page("sina") as page:
            await self.filter_file_load(page, ["image", "stylesheet", "font", "media"])

            # 先访问新浪财经首页：拟人化访问链路（真实用户先浏览首页再拉行情）并累积
            # sina 域 cookie 到上下文。注：page.request 走 Playwright HTTP 客户端（共享
            # cookie/UA），不经浏览器 TLS 栈；接口门槛仅为 Referer，故加载失败不影响后续
            try:
                await page.goto(
                    self.ENTRY_URL,
                    wait_until="domcontentloaded",
                    timeout=self.PAGE_TIMEOUT_MS,
                )
            except Exception:
                pass

            for i in range(0, len(symbols), self.CHUNK_SIZE):
                chunk = symbols[i : i + self.CHUNK_SIZE]
                text = await self._fetch_text(page, ",".join(chunk))
                if text is None:
                    return SpiderResult(
                        success=False,
                        message=f"请求失败（第{i // self.CHUNK_SIZE + 1}批）",
                    )

                # 解析本批响应：有数据的解析入 quotes，空数据/畸形行记为 no_data
                found: set[str] = set()
                for symbol, fields in self._parse_lines(text):
                    found.add(symbol)
                    if fields is None or len(fields) < 32:
                        no_data.append(symbol)
                        continue
                    quotes.append(self._parse_quote(symbol, fields))
                # 响应中缺失的请求符号（理论上不发生）也记为 no_data
                for symbol in chunk:
                    if symbol not in found:
                        no_data.append(symbol)

        if not quotes:
            return SpiderResult(
                success=False,
                message="未匹配到任何证券数据，请检查证券标识是否正确",
            )

        message = f"成功获取 {len(quotes)} 只证券的实时行情"
        if no_data:
            message += f"（{len(no_data)} 只无数据：{', '.join(no_data)}）"
        if skipped:
            message += f"（跳过 {len(skipped)} 个无效标识：{', '.join(skipped)}）"

        return SpiderResult(
            success=True,
            data={
                "total": len(quotes),
                "quotes": quotes,
                "skipped": skipped,
                "no_data": no_data,
            },
            message=message,
        )

    async def _fetch_text(self, page: Page, joined: str) -> str | None:
        """
        经浏览器上下文请求 hq.sinajs.cn 批量接口并返回 GBK 解码后的响应文本，含指数退避重试

        Args:
            page: Playwright Page 对象，使用其 request 走真实浏览器请求
            joined: 逗号连接的新浪符号列表

        Returns:
            响应文本；最终失败返回 None
        """
        url = f"{self.API_URL}?list={joined}"
        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await page.request.get(
                    url,
                    headers={"Referer": self.REFERER},
                    timeout=self.REQUEST_TIMEOUT_MS,
                )
                if response.status == 200:
                    return (await response.body()).decode("gbk", errors="replace")
            except Exception as e:
                last_error = e
            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)
        if last_error is not None:
            logger.warning(
                "sina quote fetch failed after %d retries (%s): %s",
                self.MAX_RETRIES,
                url,
                last_error,
            )
        return None

    @staticmethod
    def _normalize_symbols(identifiers: list[str]) -> tuple[list[str], list[str]]:
        """
        将证券标识列表规范化为新浪符号（前缀+6位代码），去重并保留顺序

        - 前缀格式（sh/sz/bj + 6 位代码）直接保留，如 "sh600519"
        - 裸 6 位代码按前缀推断市场：
            92/8/4 开头 → 北交所(bj)；6/5/9 开头 → 沪市(sh)；其余 → 深市(sz)

        Args:
            identifiers: 用户传入的证券标识列表

        Returns:
            (有效符号列表, 被跳过的无效标识列表)
        """
        symbols: list[str] = []
        skipped: list[str] = []
        seen: set[str] = set()
        for identifier in identifiers:
            original = identifier.strip()
            normalized = original.lower()
            if re.fullmatch(r"(sh|sz|bj)\d{6}", normalized):
                candidate = normalized
            elif re.fullmatch(r"\d{6}", normalized):
                code = normalized
                if code.startswith(("92", "8", "4")):
                    candidate = f"bj{code}"  # 北交所
                elif code.startswith(("6", "5", "9")):
                    candidate = f"sh{code}"  # 沪市：主板/科创板/ETF/B股
                else:
                    candidate = f"sz{code}"  # 深市：000/001/002/003/300/301/15x/16x/18x
            else:
                skipped.append(original)
                continue
            if candidate not in seen:
                seen.add(candidate)
                symbols.append(candidate)
        return symbols, skipped

    @staticmethod
    def _parse_lines(text: str) -> list[tuple[str, list[str] | None]]:
        """
        解析响应为 (symbol, 字段列表) 列表；无数据符号的字段为 None

        Args:
            text: hq.sinajs.cn 响应文本（GBK 已解码）

        Returns:
            (新浪符号, 逗号分割字段列表) 元组列表
        """
        rows: list[tuple[str, list[str] | None]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = RealtimeQuoteSpider.LINE_RE.match(line)
            if not m:
                continue
            symbol, content = m.group(1), m.group(2)
            if not content:
                rows.append((symbol, None))
            else:
                rows.append((symbol, content.split(",")))
        return rows

    @classmethod
    def _parse_quote(cls, symbol: str, fields: list[str]) -> dict:
        """
        解析单条行情数据（股票 / ETF / 指数共用字段布局）

        Args:
            symbol: 新浪符号，如 sh600519
            fields: 逗号分隔的字段列表

        Returns:
            解析后的数据字典
        """

        def to_float(value):
            """安全转换为 float，空值/无法解析返回 None"""
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        market = {"sh": "沪市", "sz": "深市", "bj": "北交所"}[symbol[:2]]
        code = symbol[2:]

        open_price = to_float(fields[1])
        prev_price = to_float(fields[2])
        last_price = to_float(fields[3])
        high_price = to_float(fields[4])
        low_price = to_float(fields[5])
        buy1_price = to_float(fields[6])
        sell1_price = to_float(fields[7])
        volume = to_float(fields[8])
        amount = to_float(fields[9])

        # 涨跌额 / 涨跌幅 / 振幅由开高低收计算
        change = (
            round(last_price - prev_price, 4)
            if last_price is not None and prev_price is not None
            else None
        )
        change_pct = (
            round((last_price - prev_price) / prev_price * 100, 2)
            if last_price is not None and prev_price
            else None
        )
        amplitude = (
            round((high_price - low_price) / prev_price * 100, 2)
            if high_price is not None and low_price is not None and prev_price
            else None
        )

        # 类型判定：上证指数(sh000xxx) / 深证指数(sz399xxx)；基金/ETF(5 或 1 开头)
        is_index = bool(cls.INDEX_RE.fullmatch(symbol))
        if is_index:
            security_type = "指数"
        elif code.startswith(("5", "1")):
            security_type = "基金/ETF"
        else:
            security_type = "股票"

        result = {
            "证券代码": code,
            "证券名称": fields[0],
            "市场": market,
            "类型": security_type,
            "最新价": last_price,
            "涨跌额": change,
            "涨跌幅(%)": change_pct,
            "今开": open_price,
            "昨收": prev_price,
            "最高": high_price,
            "最低": low_price,
            "振幅(%)": amplitude,
            "成交量": volume,
            "成交额(元)": amount,
            "更新时间": f"{fields[30]} {fields[31]}",
        }

        # 有盘口才附买卖五档（指数 / 停牌无盘口时省略）
        if buy1_price not in (None, 0) or sell1_price not in (None, 0):
            result["买一价"] = buy1_price
            result["卖一价"] = sell1_price
            result["五档买盘"] = [
                {"数量": to_float(fields[i]), "价格": to_float(fields[i + 1])}
                for i in range(10, 20, 2)
            ]
            result["五档卖盘"] = [
                {"数量": to_float(fields[i]), "价格": to_float(fields[i + 1])}
                for i in range(20, 30, 2)
            ]
        return result
