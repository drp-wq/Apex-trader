"""
Fair Value Gap (FVG) Engine.
Identifies 3-candle imbalance zones and tracks mitigation.
"""
from typing import List
from models.domain import Candle
from analysis.models import FVG


class FVGEngine:
    def detect_fvgs(self, candles: List[Candle]) -> List[FVG]:
        if len(candles) < 3:
            return []

        fvgs: List[FVG] = []
        n = len(candles)

        for i in range(2, n):
            c0 = candles[i - 2]
            c1 = candles[i - 1]
            c2 = candles[i]

            # Bullish FVG: c0.high < c2.low
            if c2.low > c0.high:
                gap_bottom = c0.high
                gap_top = c2.low
                fvg = FVG(
                    index=i - 1,
                    timestamp=c1.timestamp,
                    top=round(gap_top, 4),
                    bottom=round(gap_bottom, 4),
                    is_bullish=True,
                    mitigated=False
                )
                for post in candles[i + 1:]:
                    if post.low <= gap_bottom:
                        fvg.mitigated = True
                        break
                fvgs.append(fvg)

            # Bearish FVG: c0.low > c2.high
            elif c2.high < c0.low:
                gap_top = c0.low
                gap_bottom = c2.high
                fvg = FVG(
                    index=i - 1,
                    timestamp=c1.timestamp,
                    top=round(gap_top, 4),
                    bottom=round(gap_bottom, 4),
                    is_bullish=False,
                    mitigated=False
                )
                for post in candles[i + 1:]:
                    if post.high >= gap_top:
                        fvg.mitigated = True
                        break
                fvgs.append(fvg)

        return fvgs

    def get_unmitigated_fvgs(self, candles: List[Candle]) -> List[FVG]:
        return [fvg for fvg in self.detect_fvgs(candles) if not fvg.mitigated]
