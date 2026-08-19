"""
Relative Volume (RVOL) Calculation Engine.
Compares current period volume to historical moving average baselines.
"""
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RVOLMetrics:
    current_volume: float
    baseline_average_volume: float
    rvol: float
    is_high_volume: bool


class RVOLEngine:
    def __init__(self, lookback_periods: int = 20, high_volume_threshold: float = 1.5):
        self.lookback_periods = lookback_periods
        self.high_volume_threshold = high_volume_threshold

    def calculate(self, volume_series: List[float]) -> RVOLMetrics:
        """
        Computes RVOL comparing the latest volume against the prior N periods average.
        """
        if not volume_series:
            return RVOLMetrics(
                current_volume=0.0,
                baseline_average_volume=0.0,
                rvol=0.0,
                is_high_volume=False
            )

        current_vol = float(volume_series[-1])

        if len(volume_series) < 2:
            return RVOLMetrics(
                current_volume=current_vol,
                baseline_average_volume=current_vol,
                rvol=1.0 if current_vol > 0 else 0.0,
                is_high_volume=False
            )

        # Lookback window excludes the current bar
        prior_volumes = volume_series[-(self.lookback_periods + 1):-1]
        if not prior_volumes:
            baseline = current_vol
        else:
            baseline = sum(prior_volumes) / len(prior_volumes)

        if baseline <= 0.0:
            rvol = 1.0 if current_vol > 0 else 0.0
        else:
            rvol = round(current_vol / baseline, 2)

        return RVOLMetrics(
            current_volume=round(current_vol, 4),
            baseline_average_volume=round(baseline, 4),
            rvol=rvol,
            is_high_volume=rvol >= self.high_volume_threshold
        )
