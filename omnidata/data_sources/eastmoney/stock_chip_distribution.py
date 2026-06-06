"""
东方财富网股票筹码分布 Spider
获取A股个股的筹码分布数据，包括获利比例、平均成本、筹码集中度等指标

该实现基于东方财富 K 线数据，通过筹码分布算法计算得出：
- 获利比例：当前价格下获利的筹码比例
- 平均成本：所有筹码的平均持仓成本
- 90%/70% 筹码集中度：90%/70% 的筹码集中的价格区间和集中度
"""

import json
import random
import re
from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field
from py_mini_racer import MiniRacer

from omnidata.core import BaseWebSpider, SpiderResult


class StockChipDistributionParams(BaseModel):
    """股票筹码分布参数模型"""

    stock_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="股票代码，6位数字，例如：000001(平安银行)、159382(创业板人工智能ETF南方),",
    )
    adjust_type: Literal["qfq", "hfq", "none"] = Field(
        default="qfq",
        description="复权类型，可选值：qfq(前复权)、hfq(后复权)、none(不复权)，默认前复权",
    )
    kline_limit: int = Field(
        default=500,
        ge=60,
        le=2000,
        description="计算筹码分布的历史K线数量，影响计算精度：默认500条(约2年)，建议不少于100条；更多K线=更长期筹码历史=更高精度，但计算更慢",
    )
    days: int = Field(
        default=90, ge=1, le=500, description="返回最近N天的筹码分布数据，默认90天，范围1-500"
    )
    data_format: Literal["json", "dict", "markdown", "string"] = Field(
        default="json", description="返回数据格式，可选值：json, dict, string, markdown"
    )


class StockChipDistributionSpider(BaseWebSpider):
    """
    股票筹码分布 Spider

    从东方财富网获取A股个股的筹码分布数据
    通过 K 线数据和筹码分布算法计算：
    - 日期
    - 获利比例：当前价格下获利的筹码比例
    - 平均成本：所有筹码的平均持仓成本
    - 90%筹码区间：90%的筹码集中的价格区间
    - 70%筹码区间：70%的筹码集中的价格区间
    - 筹码集中度：衡量筹码集中的程度
    """

    name = "eastmoney_stock_chip_distribution"
    description = "获取A股/ETF筹码分布数据，包括获利比例、平均成本、90%/70%筹码集中度等指标，用于分析筹码结构和成本分布"
    version = "1.0.0"
    author = "noimank"
    platform = "东方财富"

    params_model = StockChipDistributionParams

    # API 配置
    API_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    DEFAULT_UT = "b2884a393a59ad64002292a3e90d46a5"

    # 复权类型映射
    ADJUST_TYPE_MAP = {
        "qfq": "1",  # 前复权
        "hfq": "2",  # 后复权
        "none": "0",  # 不复权
    }

    # 筹码分布计算 JavaScript 代码
    CYQ_CALCULATOR_JS = """
    function CYQCalculator(index, klinedata, range) {
        var maxprice = 0;
        var minprice = 0;
        var factor = 150;
        // 使用传入的range参数，默认使用最近210条数据
        var start = range ? Math.max(0, klinedata.length - range - 1) : Math.max(0, klinedata.length - 211);
        var kdata = klinedata.slice(start, Math.max(1, index + 1));
        if (kdata.length === 0) throw 'invaild index';
        for (var i = 0; i < kdata.length; i++) {
            var elements = kdata[i];
            maxprice = !maxprice ? elements.high : Math.max(maxprice, elements.high);
            minprice = !minprice ? elements.low : Math.min(minprice, elements.low);
        }

        var accuracy = Math.max(0.01, (maxprice - minprice) / (factor - 1));
        var yrange = [];
        for (var i = 0; i < factor; i++) {
            yrange.push((minprice + accuracy * i).toFixed(2) / 1);
        }
        var xdata = createNumberArray(factor);

        for (var i = 0; i < kdata.length; i++) {
            var eles = kdata[i];

            var open = eles.open,
                close = eles.close,
                high = eles.high,
                low = eles.low,
                avg = (open + close + high + low) / 4,
                turnoverRate = Math.min(1, eles.hsl / 100 || 0);

            var H = Math.floor((high - minprice) / accuracy),
                L = Math.ceil((low - minprice) / accuracy),
                GPoint = [high == low ? factor - 1 : 2 / (high - low), Math.floor((avg - minprice) / accuracy)];

            for (var n = 0; n < xdata.length; n++) {
                xdata[n] *= (1 - turnoverRate);
            }

            if (high == low) {
                xdata[GPoint[1]] += GPoint[0] * turnoverRate / 2;
            } else {
                for (var j = L; j <= H; j++) {
                    var curprice = minprice + accuracy * j;
                    if (curprice <= avg) {
                        if (Math.abs(avg - low) < 1e-8) {
                            xdata[j] += GPoint[0] * turnoverRate;
                        } else {
                            xdata[j] += (curprice - low) / (avg - low) * GPoint[0] * turnoverRate;
                        }
                    } else {
                        if (Math.abs(high - avg) < 1e-8) {
                            xdata[j] += GPoint[0] * turnoverRate;
                        } else {
                            xdata[j] += (high - curprice) / (high - avg) * GPoint[0] * turnoverRate;
                        }
                    }
                }
            }

        }

        var currentprice = klinedata[index].close;
        var totalChips = 0;
        for (var i = 0; i < factor; i++) {
            var x = xdata[i].toPrecision(12) / 1;
            totalChips += x;
        }
        var result = new CYQData();
        result.x = xdata;
        result.y = yrange;
        result.benefitPart = result.getBenefitPart(currentprice);
        result.avgCost = getCostByChip(totalChips * 0.5).toFixed(2);
        result.percentChips = {
            '90': result.computePercentChips(0.9),
            '70': result.computePercentChips(0.7)
        };
        return result;

        function getCostByChip(chip) {
            var result = 0,
                sum = 0;
            for (var i = 0; i < factor; i++) {
                var x = xdata[i].toPrecision(12) / 1;
                if (sum + x > chip) {
                    result = minprice + i * accuracy;
                    break;
                }
                sum += x;
            }
            return result;
        }

        function CYQData() {
            this.x = arguments[0];
            this.y = arguments[1];
            this.benefitPart = arguments[2];
            this.avgCost = arguments[3];
            this.percentChips = arguments[4];

            this.computePercentChips = function (percent) {
                if (percent > 1 || percent < 0) throw 'argument "percent" out of range';
                var ps = [(1 - percent) / 2, (1 + percent) / 2];
                var pr = [getCostByChip(totalChips * ps[0]), getCostByChip(totalChips * ps[1])];
                return {
                    priceRange: [pr[0].toFixed(2), pr[1].toFixed(2)],
                    concentration: pr[0] + pr[1] === 0 ? 0 : (pr[1] - pr[0]) / (pr[0] + pr[1])
                };
            };

            this.getBenefitPart = function (price) {
                var below = 0;
                for (var i = 0; i < factor; i++) {
                    var x = xdata[i].toPrecision(12) / 1;
                    if (price >= minprice + i * accuracy) {
                        below += x;
                    }
                }
                return totalChips == 0 ? 0 : below / totalChips;
            };
        }
    }

    function createNumberArray(count) {
        var array = [];
        for (var i = 0; i < count; i++) {
            array.push(0);
        }
        return array;
    }
    """

    async def crawl(self, params: StockChipDistributionParams) -> SpiderResult:
        """
        爬取股票筹码分布数据

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

                # 判断市场ID
                stock_code = params.stock_code
                if stock_code.startswith("6") or stock_code.startswith("5"):
                    market_id = "1"  # 上海
                else:
                    market_id = "0"  # 深圳

                secid = f"{market_id}.{stock_code}"

                # ── 动态提取 ut 令牌：拦截页面加载时自身发起的 push2his API 请求 ──
                captured_ut = {}

                async def capture_ut(route):
                    m = re.search(r"[?&]ut=([a-f0-9]{32})", route.request.url)
                    if m:
                        captured_ut["token"] = m.group(1)
                    await route.continue_()

                await page.route("**push2his.eastmoney.com**", capture_ut)

                await page.goto("https://data.eastmoney.com/")
                await page.wait_for_load_state("domcontentloaded", timeout=10000)

                ut = captured_ut.get("token") or self.DEFAULT_UT

                # 构建 K 线请求参数
                end_date = datetime.now().strftime("%Y%m%d")
                request_params = {
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    "ut": ut,
                    "klt": "101",  # 日线
                    "fqt": self.ADJUST_TYPE_MAP[params.adjust_type],
                    "secid": secid,
                    "end": end_date,
                    "lmt": str(params.kline_limit),
                }

                response_text = await page.evaluate(
                    """
                    async ([apiUrl, params]) => {
                        const url = new URL(apiUrl);
                        Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
                        const resp = await fetch(url.toString(), { credentials: 'include' });
                        if (!resp.ok) return null;
                        return await resp.text();
                    }
                    """,
                    [self.API_URL, request_params],
                )

                if response_text is None:
                    return SpiderResult(
                        success=False, message="请求失败"
                    )

                data = json.loads(response_text)

                # 检查返回状态
                if data.get("rc") != 0:
                    return SpiderResult(
                        success=False, message=f"获取数据失败：{data.get('rt', '未知错误')}"
                    )

                # 检查是否有数据
                kline_data = data.get("data", {})
                if not kline_data or not kline_data.get("klines"):
                    return SpiderResult(
                        success=False,
                        message=f"未找到股票代码 {params.stock_code} 的K线数据，请检查股票代码是否正确",
                    )

                # 解析 K 线数据
                kline_records = self._parse_klines(kline_data.get("klines", []))

                if len(kline_records) < 30:
                    return SpiderResult(
                        success=False,
                        message=f"K线数据不足，至少需要30条数据，当前只有{len(kline_records)}条",
                    )

                # 计算筹码分布
                chip_data = self._calculate_chip_distribution(kline_records, len(kline_records))

                # 获取最近 N 天的数据
                chip_data = chip_data.tail(params.days)

                # 获取股票名称
                stock_name = kline_data.get("name", params.stock_code)
                adjust_name = self._get_adjust_name(params.adjust_type)

                # 格式化输出
                if params.data_format == "markdown":
                    return SpiderResult(
                        success=True,
                        data=chip_data.to_markdown(),
                        message=f"成功获取 {stock_name}({params.stock_code}) {adjust_name}筹码分布数据，共{len(chip_data)}条",
                    )
                if params.data_format == "string":
                    return SpiderResult(
                        success=True,
                        data=chip_data.to_string(),
                        message=f"成功获取 {stock_name}({params.stock_code}) {adjust_name}筹码分布数据，共{len(chip_data)}条",
                    )

                # 默认返回 dict 格式
                return SpiderResult(
                    success=True,
                    data=chip_data.to_dict(orient="records"),
                    message=f"成功获取 {stock_name}({params.stock_code}) {adjust_name}筹码分布数据，共{len(chip_data)}条",
                )
        except Exception as e:
            return SpiderResult(success=False, message=f"爬取失败：{str(e)}")

    def _get_adjust_name(self, adjust_type: str) -> str:
        """获取复权类型显示名称"""
        names = {
            "qfq": "前复权",
            "hfq": "后复权",
            "none": "不复权",
        }
        return names.get(adjust_type, "前复权")

    def _parse_klines(self, klines: list[str]) -> list[dict]:
        """
        解析 K 线数据

        Args:
            klines: K线字符串列表，格式：日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率

        Returns:
            解析后的数据列表
        """
        result = []

        def safe_float(value) -> float:
            """安全地将值转换为 float"""
            if value is None or value == "" or value == "-":
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0

        for kline_str in klines:
            parts = kline_str.split(",")

            if len(parts) < 11:
                continue

            result.append(
                {
                    "date": parts[0],
                    "open": safe_float(parts[1]),
                    "close": safe_float(parts[2]),
                    "high": safe_float(parts[3]),
                    "low": safe_float(parts[4]),
                    "volume": safe_float(parts[5]),
                    "amount": safe_float(parts[6]),
                    "amplitude": safe_float(parts[7]),
                    "change_pct": safe_float(parts[8]),
                    "change_amt": safe_float(parts[9]),
                    "hsl": safe_float(parts[10]),
                }
            )

        return result

    def _calculate_chip_distribution(
        self, kline_records: list[dict], kline_limit: int = 210
    ) -> pd.DataFrame:
        """
        计算筹码分布

        Args:
            kline_records: K线数据列表
            kline_limit: 用于计算筹码分布的K线数量

        Returns:
            筹码分布 DataFrame
        """
        # 初始化 JavaScript 环境
        js_ctx = MiniRacer()
        js_ctx.eval(self.CYQ_CALCULATOR_JS)

        date_list = []
        benefit_part = []
        avg_cost = []
        pct_70_low = []
        pct_70_high = []
        pct_90_low = []
        pct_90_high = []
        pct_70_con = []
        pct_90_con = []

        for i in range(len(kline_records)):
            mcode = js_ctx.call("CYQCalculator", i, kline_records, kline_limit)

            date_list.append(kline_records[i]["date"])
            benefit_part.append(mcode["benefitPart"])
            avg_cost.append(mcode["avgCost"])
            pct_70_low.append(mcode["percentChips"]["70"]["priceRange"][0])
            pct_70_high.append(mcode["percentChips"]["70"]["priceRange"][1])
            pct_90_low.append(mcode["percentChips"]["90"]["priceRange"][0])
            pct_90_high.append(mcode["percentChips"]["90"]["priceRange"][1])
            pct_70_con.append(mcode["percentChips"]["70"]["concentration"])
            pct_90_con.append(mcode["percentChips"]["90"]["concentration"])

        df = pd.DataFrame(
            {
                "日期": date_list,
                "获利比例": benefit_part,
                "平均成本": avg_cost,
                "90%成本-下": pct_90_low,
                "90%成本-上": pct_90_high,
                "90%集中度": pct_90_con,
                "70%成本-下": pct_70_low,
                "70%成本-上": pct_70_high,
                "70%集中度": pct_70_con,
            }
        )

        # 转换数据类型（日期保持字符串格式以便JSON序列化）
        df["获利比例"] = pd.to_numeric(df["获利比例"], errors="coerce")
        df["平均成本"] = pd.to_numeric(df["平均成本"], errors="coerce")
        df["90%成本-下"] = pd.to_numeric(df["90%成本-下"], errors="coerce")
        df["90%成本-上"] = pd.to_numeric(df["90%成本-上"], errors="coerce")
        df["90%集中度"] = pd.to_numeric(df["90%集中度"], errors="coerce")
        df["70%成本-下"] = pd.to_numeric(df["70%成本-下"], errors="coerce")
        df["70%成本-上"] = pd.to_numeric(df["70%成本-上"], errors="coerce")
        df["70%集中度"] = pd.to_numeric(df["70%集中度"], errors="coerce")

        return df
