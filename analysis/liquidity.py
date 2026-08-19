"""
Liquidity Engine.
Identifies Buy-Side (BSL) and Sell-Side (SSL) liquidity levels and sweep patterns.
"""
from typing import List
from models.domain import Candle
from analysis.models import LiquidityLevel, LiquidityType


class LiquidityEngine:
    def __init__(self, swing_lookback: int = 2):
        self.swing_lookback = swing_lookback

    def detect_liquidity_pools(self, candles: List[Candle]) -> List[LiquidityLevel]:
        if len(candles) < (self.swing_lookback * 2 + 1):
            return []

        pools: List[LiquidityLevel] = []
        n = len(candles)

        for i in range(self.swing_lookback, n - self.swing_lookback):
            c = candles[i]
            # BSL Check
            if all(c.high >= candles[i - j].high for j in range(1, self.swing_lookback + 1)) and \
               all(c.high > candles[i + j].high for j in range(1, self.swing_lookback + 1)):
                swept = any(post.high > c.high for post in candles[i + 1:])
                pools.append(LiquidityLevel(i, c.timestamp, c.high, LiquidityType.BSL, swept=swept))

            # SSL Check
            if all(c.low <= candles[i - j].low for j in range(1, self.swing_lookback + 1)) and \
               all(c.low < candles[i + j].low for j in range(1, self.swing_lookback + 1)):
                swept = any(post.low < c.low for post in candles[i + 1:])
                pools.append(LiquidityLevel(i, c.timestamp, c.low, LiquidityType.SSL, swept=swept))

        return pools

    def detect_sweeps(self, candles: List[Candle]) -> List[LiquidityLevel]:
        pools = self.detect_liquidity_pools(candles)
        return [p for p in pools if p.swept]
