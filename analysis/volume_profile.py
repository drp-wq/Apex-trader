"""
Volume Profile Engine.
Calculates Point of Control (POC) and Value Area (VAH / VAL).
"""
from typing import List
from models.domain import Candle
from analysis.models import VolumeProfileResult


class VolumeProfileEngine:
    def __init__(self, num_bins: int = 20, value_area_pct: float = 0.70):
        self.num_bins = num_bins
        self.value_area_pct = value_area_pct

    def calculate(self, candles: List[Candle]) -> VolumeProfileResult:
        if not candles:
            return VolumeProfileResult(0.0, 0.0, 0.0, 0.0)

        lowest = min(c.low for c in candles)
        highest = max(c.high for c in candles)
        total_volume = sum(c.volume for c in candles)

        if highest == lowest or total_volume == 0.0:
            mid = (highest + lowest) / 2.0
            return VolumeProfileResult(mid, highest, lowest, total_volume)

        bin_width = (highest - lowest) / self.num_bins
        bins = [0.0] * self.num_bins
        bin_prices = [lowest + (i + 0.5) * bin_width for i in range(self.num_bins)]

        for c in candles:
            avg_p = (c.high + c.low + c.close) / 3.0
            bin_idx = int((avg_p - lowest) / bin_width)
            if bin_idx >= self.num_bins:
                bin_idx = self.num_bins - 1
            bins[bin_idx] += c.volume

        max_vol_idx = bins.index(max(bins))
        poc_price = round(bin_prices[max_vol_idx], 4)

        target_volume = total_volume * self.value_area_pct
        curr_volume = bins[max_vol_idx]
        left = max_vol_idx
        right = max_vol_idx

        while curr_volume < target_volume and (left > 0 or right < self.num_bins - 1):
            left_vol = bins[left - 1] if left > 0 else -1.0
            right_vol = bins[right + 1] if right < self.num_bins - 1 else -1.0

            if left_vol >= right_vol and left > 0:
                left -= 1
                curr_volume += bins[left]
            elif right < self.num_bins - 1:
                right += 1
                curr_volume += bins[right]
            elif left > 0:
                left -= 1
                curr_volume += bins[left]
            else:
                break

        val_price = round(bin_prices[left] - (bin_width / 2.0), 4)
        vah_price = round(bin_prices[right] + (bin_width / 2.0), 4)

        return VolumeProfileResult(
            poc=poc_price,
            vah=vah_price,
            val=val_price,
            total_volume=round(total_volume, 4)
        )
