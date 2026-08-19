"""
Order Block (OB) Engine.
Identifies institutional footprints preceding energetic displacement moves.
"""
from typing import List
from models.domain import Candle
from analysis.models import OrderBlock


class OrderBlockEngine:
    def __init__(self, displacement_multiplier: float = 1.5):
        self.displacement_multiplier = displacement_multiplier

    def detect_order_blocks(self, candles: List[Candle]) -> List[OrderBlock]:
        if len(candles) < 3:
            return []

        obs: List[OrderBlock] = []
        avg_body = sum(abs(c.close - c.open) for c in candles) / len(candles) if candles else 1.0

        for i in range(len(candles) - 2):
            curr = candles[i]
            nxt = candles[i + 1]

            curr_body = abs(curr.close - curr.open)
            nxt_body = abs(nxt.close - nxt.open)

            # Bullish OB: Bearish candle followed by strong bullish displacement
            if curr.close < curr.open and nxt.close > nxt.open and nxt_body >= (avg_body * self.displacement_multiplier) and nxt.close > curr.high:
                ob = OrderBlock(
                    index=i,
                    timestamp=curr.timestamp,
                    top=curr.high,
                    bottom=curr.low,
                    is_bullish=True,
                    mitigated=False
                )
                for post in candles[i + 2:]:
                    if post.low <= ob.bottom:
                        ob.mitigated = True
                        break
                obs.append(ob)

            # Bearish OB: Bullish candle followed by strong bearish displacement
            elif curr.close > curr.open and nxt.close < nxt.open and nxt_body >= (avg_body * self.displacement_multiplier) and nxt.close < curr.low:
                ob = OrderBlock(
                    index=i,
                    timestamp=curr.timestamp,
                    top=curr.high,
                    bottom=curr.low,
                    is_bullish=False,
                    mitigated=False
                )
                for post in candles[i + 2:]:
                    if post.high >= ob.top:
                        ob.mitigated = True
                        break
                obs.append(ob)

        return obs

    def get_unmitigated_obs(self, candles: List[Candle]) -> List[OrderBlock]:
        return [ob for ob in self.detect_order_blocks(candles) if not ob.mitigated]
