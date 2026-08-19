"""
Deterministic Confluence Engine.
Evaluates SMC metrics and applies immutable hard gates before generating trade decisions.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time

from models.domain import Candle, TrendState, SignalDirection, Provenance
from scanner.rvol_engine import RVOLMetrics
from analysis.models import (
    MarketStructureResult,
    FVG,
    OrderBlock,
    LiquidityLevel,
    VolumeProfileResult,
)


class ConfluenceDecision(str, Enum):
    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True)
class ConfluenceResult:
    decision: ConfluenceDecision
    symbol: str
    direction: SignalDirection
    score: float
    reasons: List[str]
    rejection_reasons: List[str]
    entry_zone_high: float
    entry_zone_low: float
    invalidation_price: float
    confidence: float
    timestamp: float
    provenance: Provenance


class ConfluenceEngine:
    def __init__(
        self,
        min_score: float = 70.0,
        min_rvol: float = 1.2,
        require_unmitigated_zone: bool = True
    ):
        self.min_score = min_score
        self.min_rvol = min_rvol
        self.require_unmitigated_zone = require_unmitigated_zone

    def evaluate(
        self,
        symbol: str,
        candles: List[Candle],
        structure: MarketStructureResult,
        fvgs: List[FVG],
        obs: List[OrderBlock],
        sweeps: List[LiquidityLevel],
        rvol_metrics: RVOLMetrics,
        volume_profile: Optional[VolumeProfileResult] = None,
        provenance: Provenance = Provenance.PAPER
    ) -> ConfluenceResult:
        """
        Executes deterministic multi-factor confluence scoring.
        Applies fail-closed hard gates.
        """
        if not isinstance(structure.trend, TrendState):
            raise ValueError(f"Invalid TrendState received: {structure.trend}")

        reasons: List[str] = []
        rejection_reasons: List[str] = []
        score: float = 0.0

        ts = candles[-1].timestamp if candles else time.time()
        curr_price = candles[-1].close if candles else 0.0

        # Determine bias
        if structure.trend == TrendState.BULLISH:
            direction = SignalDirection.BUY
        elif structure.trend == TrendState.BEARISH:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.HOLD

        # --- HARD GATE 1: Trend Alignment ---
        if structure.trend == TrendState.RANGING:
            rejection_reasons.append("HARD GATE: Trend is RANGING. Directional bias undefined.")

        # --- HARD GATE 2: RVOL Threshold ---
        if rvol_metrics.rvol < self.min_rvol:
            rejection_reasons.append(
                f"HARD GATE: RVOL {rvol_metrics.rvol} below minimum required {self.min_rvol}."
            )

        # Unmitigated zone filtering
        active_obs = [ob for ob in obs if not ob.mitigated and ob.is_bullish == (direction == SignalDirection.BUY)]
        active_fvgs = [fvg for fvg in fvgs if not fvg.mitigated and fvg.is_bullish == (direction == SignalDirection.BUY)]

        # --- HARD GATE 3: Unmitigated POI Zone ---
        if self.require_unmitigated_zone and direction != SignalDirection.HOLD:
            if not active_obs and not active_fvgs:
                rejection_reasons.append("HARD GATE: No valid unmitigated OB or FVG anchor found.")

        # Determine Entry Zone and Invalidation Stop
        entry_high = curr_price
        entry_low = curr_price
        invalidation = 0.0

        if direction == SignalDirection.BUY:
            if active_obs:
                entry_high = max(ob.top for ob in active_obs)
                entry_low = min(ob.bottom for ob in active_obs)
                invalidation = entry_low * 0.998
            elif active_fvgs:
                entry_high = max(fvg.top for fvg in active_fvgs)
                entry_low = min(fvg.bottom for fvg in active_fvgs)
                invalidation = entry_low * 0.998
            elif structure.swing_lows:
                invalidation = structure.swing_lows[-1].price * 0.998
        elif direction == SignalDirection.SELL:
            if active_obs:
                entry_high = max(ob.top for ob in active_obs)
                entry_low = min(ob.bottom for ob in active_obs)
                invalidation = entry_high * 1.002
            elif active_fvgs:
                entry_high = max(fvg.top for fvg in active_fvgs)
                entry_low = min(fvg.bottom for fvg in active_fvgs)
                invalidation = entry_high * 1.002
            elif structure.swing_highs:
                invalidation = structure.swing_highs[-1].price * 1.002

        # --- Scoring Factors ---
        if structure.trend in (TrendState.BULLISH, TrendState.BEARISH):
            score += 30.0
            reasons.append(f"Trend aligned with market structure ({structure.trend.value}).")

        if active_obs:
            score += 25.0
            reasons.append(f"Anchored to {len(active_obs)} unmitigated Order Block(s).")

        if active_fvgs:
            score += 20.0
            reasons.append(f"Fair Value Gap imbalance confluence ({len(active_fvgs)} active).")

        if sweeps:
            score += 15.0
            reasons.append("Recent liquidity sweep confirmed.")

        if rvol_metrics.rvol >= self.min_rvol:
            score += 10.0
            reasons.append(f"Volume expansion verified (RVOL: {rvol_metrics.rvol}).")

        if volume_profile and volume_profile.poc > 0:
            if direction == SignalDirection.BUY and curr_price >= volume_profile.poc:
                score += 10.0
                reasons.append("Price trading above Volume Profile POC.")
            elif direction == SignalDirection.SELL and curr_price <= volume_profile.poc:
                score += 10.0
                reasons.append("Price trading below Volume Profile POC.")

        # Hard gate enforcement
        if rejection_reasons or score < self.min_score or direction == SignalDirection.HOLD:
            return ConfluenceResult(
                decision=ConfluenceDecision.NO_TRADE,
                symbol=symbol,
                direction=direction,
                score=round(score, 2),
                reasons=reasons,
                rejection_reasons=rejection_reasons,
                entry_zone_high=round(entry_high, 4),
                entry_zone_low=round(entry_low, 4),
                invalidation_price=round(invalidation, 4),
                confidence=round(min(score / 100.0, 1.0), 2),
                timestamp=ts,
                provenance=provenance
            )

        return ConfluenceResult(
            decision=ConfluenceDecision.TRADE,
            symbol=symbol,
            direction=direction,
            score=round(score, 2),
            reasons=reasons,
            rejection_reasons=[],
            entry_zone_high=round(entry_high, 4),
            entry_zone_low=round(entry_low, 4),
            invalidation_price=round(invalidation, 4),
            confidence=round(min(score / 100.0, 1.0), 2),
            timestamp=ts,
            provenance=provenance
        )
