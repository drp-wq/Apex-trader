"""
Aggregated Market Metrics Pipeline.
Combines price changes, volume profile metrics, OI, and RVOL.
"""
from dataclasses import dataclass
from typing import List, Optional
from models.domain import Candle
from scanner.oi_engine import OIEngine, OIMetrics
from scanner.rvol_engine import RVOLEngine, RVOLMetrics


@dataclass(frozen=True)
class MarketMetricsSnapshot:
    symbol: str
    latest_price: float
    price_change_pct: float
    oi_metrics: OIMetrics
    rvol_metrics: RVOLMetrics
    is_favorable_momentum: bool


class MarketMetricsEngine:
    def __init__(
        self,
        oi_engine: Optional[OIEngine] = None,
        rvol_engine: Optional[RVOLEngine] = None,
        min_rvol_favorable: float = 1.5
    ):
        self.oi_engine = oi_engine or OIEngine()
        self.rvol_engine = rvol_engine or RVOLEngine()
        self.min_rvol_favorable = min_rvol_favorable

    def compute_snapshot(
        self,
        candles: List[Candle],
        oi_history: List[float]
    ) -> MarketMetricsSnapshot:
        """
        Builds a normalized snapshot from raw candles and OI history.
        """
        if not candles:
            empty_oi = self.oi_engine.analyze([])
            empty_rvol = self.rvol_engine.calculate([])
            return MarketMetricsSnapshot(
                symbol="UNKNOWN",
                latest_price=0.0,
                price_change_pct=0.0,
                oi_metrics=empty_oi,
                rvol_metrics=empty_rvol,
                is_favorable_momentum=False
            )

        symbol = candles[-1].symbol
        latest_price = candles[-1].close

        if len(candles) >= 2 and candles[0].open > 0:
            price_change_pct = round(
                ((latest_price - candles[0].open) / candles[0].open) * 100.0, 4
            )
        else:
            price_change_pct = 0.0

        vol_series = [c.volume for c in candles]
        rvol = self.rvol_engine.calculate(vol_series)
        oi = self.oi_engine.analyze(oi_history)

        is_favorable = rvol.rvol >= self.min_rvol_favorable and (oi.oi_change_pct > 0 or rvol.is_high_volume)

        return MarketMetricsSnapshot(
            symbol=symbol,
            latest_price=latest_price,
            price_change_pct=price_change_pct,
            oi_metrics=oi,
            rvol_metrics=rvol,
            is_favorable_momentum=is_favorable
        )
