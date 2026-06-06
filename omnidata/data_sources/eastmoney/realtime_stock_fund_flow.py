"""
东方财富网个股/指数资金流 Spider
获取个股或指数的实时资金流向数据

从 https://data.eastmoney.com/zjlx/ 页面获取数据
支持输入股票代码或指数代码查询资金流向
"""

import random
import re
from datetime import datetime

from pydantic import BaseModel, Field

from omnidata.core import BaseWebSpider, SpiderResult


class RealtimeStockFundFlowParams(BaseModel):
    """个股/指数资金流参数模型"""

    secid: str = Field(
        ...,
        description="证券ID，格式：市场ID.代码，例如：1.000001(上证指数)、0.000001(平安银行)、1.516920（芯片ETF）。市场ID：0=深圳，1=上海",
    )


class RealtimeStockFundFlowSpider(BaseWebSpider):
    """
    个股/指数资金流 Spider

    从东方财富网获取个股或指数的实时资金流向数据
    包括主力净流入、超大单、大单、中单、小单的资金流向数据
    以及5日、10日累计资金流向
    """

    name = "eastmoney_realtime_stock_fund_flow"
    description = "获取个股、指数、ETF基金的实时资金流向数据，包括主力、超大单、大单、中单、小单的净流入及占比，以及5日、10日累计资金流向"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = RealtimeStockFundFlowParams

    # API 配置
    API_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    DEFAULT_UT = "b2884a393a59ad64002292a3e90d46a5"
    # 请求字段：包含所有资金流向相关字段
    FIELDS = "f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f64,f65,f70,f71,f76,f77,f82,f83,f164,f166,f168,f170,f172,f252,f253,f254,f255,f256,f124,f6,f278,f279,f280,f281,f282"

    async def crawl(self, params: RealtimeStockFundFlowParams) -> SpiderResult:
        """
        爬取个股/指数资金流数据

        Args:
            params: 验证后的参数对象

        Returns:
            SpiderResult: 执行结果
        """
        try:
            async with self.new_page("eastmoney") as page:
                await self.filter_file_load(
                    page, ["image", "stylesheet", "font", "media"]
                )

                # ── 动态提取 ut 令牌：拦截页面加载时自身发起的 push2 API 请求 ──
                captured_ut = {}

                async def capture_ut(route):
                    m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                    if m:
                        captured_ut["token"] = m.group(1)
                    await route.continue_()

                await page.route("**push2.eastmoney.com**", capture_ut)

                await page.goto("https://data.eastmoney.com/")
                await page.wait_for_load_state("domcontentloaded", timeout=10000)

                ut = captured_ut.get("token") or self.DEFAULT_UT

                # 构建请求参数
                request_params = {
                    "fltt": "2",
                    "secids": params.secid,
                    "fields": self.FIELDS,
                    "ut": ut,
                }

                result = await page.evaluate(
                    """
                    async ([apiUrl, params]) => {
                        const url = new URL(apiUrl);
                        Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
                        const resp = await fetch(url.toString(), { credentials: 'include' });
                        if (!resp.ok) return null;
                        return await resp.json();
                    }
                    """,
                    [self.API_URL, request_params],
                )

                if result is None:
                    return SpiderResult(
                        success=False, message="请求失败"
                    )

                # 解析响应
                data = result

                # 检查返回状态
                if data.get("rc") != 0:
                    return SpiderResult(
                        success=False, message=f"获取数据失败：{data.get('msg', '未知错误')}"
                    )

                # 检查是否有数据
                diff_data = data.get("data", {}).get("diff", [])
                if not diff_data:
                    return SpiderResult(
                        success=False,
                        message=f"未找到证券ID {params.secid} 的数据，请检查证券ID是否正确",
                    )

                # 解析数据
                result_data = self._parse_fund_flow(diff_data[0], params)

                return SpiderResult(
                    success=True,
                    data=result_data,
                    message=f"成功获取 {params.secid} 的资金流向数据",
                )
        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _parse_fund_flow(self, item: dict, params: RealtimeStockFundFlowParams) -> dict:
        """
        解析资金流向数据

        Args:
            item: API返回的单条数据
            params: 请求参数

        Returns:
            解析后的数据字典
        """

        def safe_float(value) -> float:
            """安全地将值转换为 float"""
            if value is None or value == "":
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0

        def safe_int(value) -> int:
            """安全地将值转换为 int"""
            if value is None or value == "":
                return 0
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0

        # 基础数据
        # f6 = safe_float(item.get("f6"))  # 最新价
        f124 = safe_int(item.get("f124"))  # 更新时间戳

        # 主力资金
        f62 = safe_float(item.get("f62"))  # 主力净流入（元）
        f184 = safe_float(item.get("f184"))  # 主力净占比（%）
        f64 = safe_float(item.get("f64"))  # 主力买入（元）
        f65 = safe_float(item.get("f65"))  # 主力卖出（元）

        # 超大单
        f66 = safe_float(item.get("f66"))  # 超大单净流入（元）
        f69 = safe_float(item.get("f69"))  # 超大单净占比（%）

        # 大单
        f70 = safe_float(item.get("f70"))  # 大单买入（元）
        f71 = safe_float(item.get("f71"))  # 大单卖出（元）
        f72 = safe_float(item.get("f72"))  # 大单净流入（元）
        f75 = safe_float(item.get("f75"))  # 大单净占比（%）

        # 中单
        f76 = safe_float(item.get("f76"))  # 中单买入（元）
        f77 = safe_float(item.get("f77"))  # 中单卖出（元）
        f78 = safe_float(item.get("f78"))  # 中单净流入（元）
        f81 = safe_float(item.get("f81"))  # 中单净占比（%）

        # 小单
        f82 = safe_float(item.get("f82"))  # 小单买入（元）
        f83 = safe_float(item.get("f83"))  # 小单卖出（元）
        f84 = safe_float(item.get("f84"))  # 小单净流入（元）
        f87 = safe_float(item.get("f87"))  # 小单净占比（%）

        # 5日累计
        f164 = safe_float(item.get("f164"))  # 5日主力净流入（元）
        f166 = safe_float(item.get("f166"))  # 5日超大单净流入（元）
        f168 = safe_float(item.get("f168"))  # 5日大单净流入（元）
        f170 = safe_float(item.get("f170"))  # 5日中单净流入（元）
        f172 = safe_float(item.get("f172"))  # 5日小单净流入（元）

        # 10日累计
        f252 = safe_float(item.get("f252"))  # 10日主力净流入（元）
        f253 = safe_float(item.get("f253"))  # 10日超大单净流入（元）
        f254 = safe_float(item.get("f254"))  # 10日大单净流入（元）
        f255 = safe_float(item.get("f255"))  # 10日中单净流入（元）
        f256 = safe_float(item.get("f256"))  # 10日小单净流入（元）

        # 更新时间
        update_time = datetime.fromtimestamp(f124).strftime("%Y-%m-%d %H:%M:%S") if f124 else ""

        # 构建返回数据
        result = {
            "证券ID": params.secid,
            # "证券名称": params.sec_name,
            # "最新价": round(f6, 2),
            "更新时间": update_time,
            "今日资金流向": {
                "主力": {
                    "净流入(亿元)": round(f62 / 100000000, 2),
                    "净占比(%)": round(f184, 2),
                    "买入(亿元)": round(f64 / 100000000, 2),
                    "卖出(亿元)": round(f65 / 100000000, 2),
                },
                "超大单": {
                    "净流入(亿元)": round(f66 / 100000000, 2),
                    "净占比(%)": round(f69, 2),
                },
                "大单": {
                    "买入(亿元)": round(f70 / 100000000, 2),
                    "卖出(亿元)": round(f71 / 100000000, 2),
                    "净流入(亿元)": round(f72 / 100000000, 2),
                    "净占比(%)": round(f75, 2),
                },
                "中单": {
                    "买入(亿元)": round(f76 / 100000000, 2),
                    "卖出(亿元)": round(f77 / 100000000, 2),
                    "净流入(亿元)": round(f78 / 100000000, 2),
                    "净占比(%)": round(f81, 2),
                },
                "小单": {
                    "买入(亿元)": round(f82 / 100000000, 2),
                    "卖出(亿元)": round(f83 / 100000000, 2),
                    "净流入(亿元)": round(f84 / 100000000, 2),
                    "净占比(%)": round(f87, 2),
                },
            },
            "5日累计资金流向": {
                "主力净流入(亿元)": round(f164 / 100000000, 2),
                "超大单净流入(亿元)": round(f166 / 100000000, 2),
                "大单净流入(亿元)": round(f168 / 100000000, 2),
                "中单净流入(亿元)": round(f170 / 100000000, 2),
                "小单净流入(亿元)": round(f172 / 100000000, 2),
            },
            "10日累计资金流向": {
                "主力净流入(亿元)": round(f252 / 100000000, 2),
                "超大单净流入(亿元)": round(f253 / 100000000, 2),
                "大单净流入(亿元)": round(f254 / 100000000, 2),
                "中单净流入(亿元)": round(f255 / 100000000, 2),
                "小单净流入(亿元)": round(f256 / 100000000, 2),
            },
        }

        return result
