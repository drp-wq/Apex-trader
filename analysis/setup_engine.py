"""
Deterministic Trade Setup Engine for APEX TRADER.
Converts valid confluence decisions into structured multi-target trade plans.
Does NOT perform any exchange calls, balance mutations, or order executions.
"""
from dataclasses import dataclass
from typing import List, Optional
import time

from models.domain import SignalDirection, Provenance
from analysis.confluence import ConfluenceResult, ConfluenceDecision


@dataclass(frozen=True)
class TradeSetup:
    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    rr_tp1: float
    rr_tp2: float
    rr_tp3: float
    risk_distance: float
    score: float
    confidence: float
    reasons: List[str]
    timestamp: float
    provenance: Provenance
    is_valid: bool
    rejection_reason: Optional[str] = None


class TradeSetupEngine:
    def __init__(
        self,
        tp1_rr_multiplier: float = 2.0,
        tp2_rr_multiplier: float = 3.0,
        tp3_rr_multiplier: float = 5.0
    ):
        self.tp1_rr = tp1_rr_multiplier
        self.tp2_rr = tp2_rr_multiplier
        self.tp3_rr = tp3_rr_multiplier

    def generate_setup(self, confluence: ConfluenceResult) -> TradeSetup:
        """
        Transforms a ConfluenceResult into a TradeSetup.
        Fails closed with is_valid=False if the confluence decision is NO_TRADE.
        """
        # Hard Gate: Rejection check
        if confluence.decision != ConfluenceDecision.TRADE:
            return TradeSetup(
                symbol=confluence.symbol,
                direction=confluence.direction,
                entry_price=0.0,
                stop_loss=0.0,
                tp1=0.0,
                tp2=0.0,
                tp3=0.0,
                rr_tp1=0.0,
                rr_tp2=0.0,
                rr_tp3=0.0,
                risk_distance=0.0,
                score=confluence.score,
                confidence=confluence.confidence,
                reasons=confluence.reasons,
                timestamp=confluence.timestamp,
                provenance=confluence.provenance,
                is_valid=False,
                rejection_reason="Confluence decision was NO_TRADE."
            )

        if confluence.direction not in (SignalDirection.BUY, SignalDirection.SELL):
            return TradeSetup(
                symbol=confluence.symbol,
                direction=confluence.direction,
                entry_price=0.0,
                stop_loss=0.0,
                tp1=0.0,
                tp2=0.0,
                tp3=0.0,
                rr_tp1=0.0,
                rr_tp2=0.0,
                rr_tp3=0.0,
                risk_distance=0.0,
                score=confluence.score,
                confidence=confluence.confidence,
                reasons=confluence.reasons,
                timestamp=confluence.timestamp,
                provenance=confluence.provenance,
                is_valid=False,
                rejection_reason=f"Invalid signal direction: {confluence.direction}."
            )

        # Entry approximation: Zone midpoint
        entry_price = round((confluence.entry_zone_high + confluence.entry_zone_low) / 2.0, 4)
        stop_loss = round(confluence.invalidation_price, 4)
        risk_distance = round(abs(entry_price - stop_loss), 4)

        if risk_distance <= 0:
            return TradeSetup(
                symbol=confluence.symbol,
                direction=confluence.direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                tp1=0.0,
                tp2=0.0,
                tp3=0.0,
                rr_tp1=0.0,
                rr_tp2=0.0,
                rr_tp3=0.0,
                risk_distance=0.0,
                score=confluence.score,
                confidence=confluence.confidence,
                reasons=confluence.reasons,
                timestamp=confluence.timestamp,
                provenance=confluence.provenance,
                is_valid=False,
                rejection_reason="Risk distance cannot be zero."
            )

        # Target calculation
        if confluence.direction == SignalDirection.BUY:
            if stop_loss >= entry_price:
                return TradeSetup(
                    symbol=confluence.symbol,
                    direction=confluence.direction,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    tp1=0.0,
                    tp2=0.0,
                    tp3=0.0,
                    rr_tp1=0.0,
                    rr_tp2=0.0,
                    rr_tp3=0.0,
                    risk_distance=risk_distance,
                    score=confluence.score,
                    confidence=confluence.confidence,
                    reasons=confluence.reasons,
                    timestamp=confluence.timestamp,
                    provenance=confluence.provenance,
                    is_valid=False,
                    rejection_reason="Long stop-loss must be strictly below entry price."
                )
            tp1 = round(entry_price + (risk_distance * self.tp1_rr), 4)
            tp2 = round(entry_price + (risk_distance * self.tp2_rr), 4)
            tp3 = round(entry_price + (risk_distance * self.tp3_rr), 4)
        else:
            if stop_loss <= entry_price:
                return TradeSetup(
                    symbol=confluence.symbol,
                    direction=confluence.direction,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    tp1=0.0,
                    tp2=0.0,
                    tp3=0.0,
                    rr_tp1=0.0,
                    rr_tp2=0.0,
                    rr_tp3=0.0,
                    risk_distance=risk_distance,
                    score=confluence.score,
                    confidence=confluence.confidence,
                    reasons=confluence.reasons,
                    timestamp=confluence.timestamp,
                    provenance=confluence.provenance,
                    is_valid=False,
                    rejection_reason="Short stop-loss must be strictly above entry price."
                )
            tp1 = round(entry_price - (risk_distance * self.tp1_rr), 4)
            tp2 = round(entry_price - (risk_distance * self.tp2_rr), 4)
            tp3 = round(entry_price - (risk_distance * self.tp3_rr), 4)

        return TradeSetup(
            symbol=confluence.symbol,
            direction=confluence.direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            rr_tp1=self.tp1_rr,
            rr_tp2=self.tp2_rr,
            rr_tp3=self.tp3_rr,
            risk_distance=risk_distance,
            score=confluence.score,
            confidence=confluence.confidence,
            reasons=confluence.reasons,
            timestamp=confluence.timestamp,
            provenance=confluence.provenance,
            is_valid=True
        )
