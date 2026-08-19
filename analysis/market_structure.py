"""
Market Structure Engine.
Detects swing highs/lows, Break of Structure (BOS), and Change of Character (CHOCH).
"""
from typing import List, Tuple
from models.domain import Candle, TrendState
from analysis.models import SwingPoint, StructureBreak, StructureType, MarketStructureResult


class MarketStructureEngine:
    def __init__(self, left_bars: int = 2, right_bars: int = 2):
        self.left_bars = left_bars
        self.right_bars = right_bars

    def detect_swings(self, candles: List[Candle]) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        swing_highs: List[SwingPoint] = []
        swing_lows: List[SwingPoint] = []
        n = len(candles)

        for i in range(self.left_bars, n - self.right_bars):
            curr_high = candles[i].high
            curr_low = candles[i].low

            # Swing High Check
            is_sh = all(curr_high >= candles[i - j].high for j in range(1, self.left_bars + 1)) and \
                    all(curr_high > candles[i + j].high for j in range(1, self.right_bars + 1))
            if is_sh:
                swing_highs.append(SwingPoint(i, candles[i].timestamp, curr_high, is_high=True))

            # Swing Low Check
            is_sl = all(curr_low <= candles[i - j].low for j in range(1, self.left_bars + 1)) and \
                    all(curr_low < candles[i + j].low for j in range(1, self.right_bars + 1))
            if is_sl:
                swing_lows.append(SwingPoint(i, candles[i].timestamp, curr_low, is_high=False))

        return swing_highs, swing_lows

    def analyze(self, candles: List[Candle]) -> MarketStructureResult:
        if len(candles) < (self.left_bars + self.right_bars + 1):
            return MarketStructureResult(
                trend=TrendState.RANGING,
                swing_highs=[],
                swing_lows=[],
                breaks=[]
            )

        swing_highs, swing_lows = self.detect_swings(candles)
        breaks: List[StructureBreak] = []
        trend = TrendState.RANGING

        last_sh = None
        last_sl = None

        for i, candle in enumerate(candles):
            active_sh = [sh for sh in swing_highs if sh.index < i]
            active_sl = [sl for sl in swing_lows if sl.index < i]

            if active_sh:
                recent_sh = active_sh[-1]
                if candle.close > recent_sh.price and (last_sh is None or recent_sh.index != last_sh.index):
                    b_type = StructureType.BOS if trend == TrendState.BULLISH else StructureType.CHOCH
                    breaks.append(StructureBreak(i, candle.timestamp, candle.close, b_type, "BULLISH"))
                    trend = TrendState.BULLISH
                    last_sh = recent_sh

            if active_sl:
                recent_sl = active_sl[-1]
                if candle.close < recent_sl.price and (last_sl is None or recent_sl.index != last_sl.index):
                    b_type = StructureType.BOS if trend == TrendState.BEARISH else StructureType.CHOCH
                    breaks.append(StructureBreak(i, candle.timestamp, candle.close, b_type, "BEARISH"))
                    trend = TrendState.BEARISH
                    last_sl = recent_sl

        if not breaks:
            if len(swing_highs) >= 2 and len(swing_lows) >= 2:
                if swing_highs[-1].price > swing_highs[-2].price and swing_lows[-1].price > swing_lows[-2].price:
                    trend = TrendState.BULLISH
                elif swing_highs[-1].price < swing_highs[-2].price and swing_lows[-1].price < swing_lows[-2].price:
                    trend = TrendState.BEARISH
                else:
                    trend = TrendState.RANGING

        return MarketStructureResult(
            trend=trend,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            breaks=breaks
        )
