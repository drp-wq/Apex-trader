import pytest
from models.domain import Candle, TrendState, SignalDirection, Provenance
from scanner.rvol_engine import RVOLMetrics
from analysis.models import (
    MarketStructureResult,
    FVG,
    OrderBlock,
    LiquidityLevel,
    LiquidityType,
    VolumeProfileResult,
)
from analysis.confluence import ConfluenceEngine, ConfluenceDecision


def test_confluence_bullish_valid_trade():
    engine = ConfluenceEngine(min_score=70.0, min_rvol=1.2)
    candles = [Candle("BTCUSDT", 100.0, 50000, 51000, 49500, 50800, 20.0)]
    structure = MarketStructureResult(TrendState.BULLISH, [], [], [])
    obs = [OrderBlock(0, 100.0, top=50200.0, bottom=49800.0, is_bullish=True, mitigated=False)]
    fvgs = [FVG(0, 100.0, top=50600.0, bottom=50400.0, is_bullish=True, mitigated=False)]
    sweeps = [LiquidityLevel(0, 100.0, 49500.0, LiquidityType.SSL, swept=True)]
    rvol = RVOLMetrics(20.0, 10.0, 2.0, True)
    vp = VolumeProfileResult(poc=50100.0, vah=51000.0, val=49500.0, total_volume=20.0)

    res = engine.evaluate("BTCUSDT", candles, structure, fvgs, obs, sweeps, rvol, vp)
    assert res.decision == ConfluenceDecision.TRADE
    assert res.direction == SignalDirection.BUY
    assert res.score >= 70.0
    assert len(res.rejection_reasons) == 0
    assert res.invalidation_price < 50000.0


def test_confluence_ranging_hard_gate_rejection():
    engine = ConfluenceEngine()
    candles = [Candle("BTCUSDT", 100.0, 50000, 50500, 49500, 50000, 10.0)]
    structure = MarketStructureResult(TrendState.RANGING, [], [], [])
    rvol = RVOLMetrics(15.0, 10.0, 1.5, True)

    res = engine.evaluate("BTCUSDT", candles, structure, [], [], [], rvol)
    assert res.decision == ConfluenceDecision.NO_TRADE
    assert any("Trend is RANGING" in r for r in res.rejection_reasons)


def test_confluence_missing_zone_hard_gate_rejection():
    engine = ConfluenceEngine(require_unmitigated_zone=True)
    candles = [Candle("BTCUSDT", 100.0, 50000, 51000, 49500, 50800, 20.0)]
    structure = MarketStructureResult(TrendState.BULLISH, [], [], [])
    rvol = RVOLMetrics(20.0, 10.0, 2.0, True)

    # No OBs and no FVGs
    res = engine.evaluate("BTCUSDT", candles, structure, [], [], [], rvol)
    assert res.decision == ConfluenceDecision.NO_TRADE
    assert any("No valid unmitigated OB or FVG" in r for r in res.rejection_reasons)


def test_confluence_low_rvol_hard_gate_rejection():
    engine = ConfluenceEngine(min_rvol=1.5)
    candles = [Candle("BTCUSDT", 100.0, 50000, 51000, 49500, 50800, 5.0)]
    structure = MarketStructureResult(TrendState.BULLISH, [], [], [])
    obs = [OrderBlock(0, 100.0, top=50200.0, bottom=49800.0, is_bullish=True, mitigated=False)]
    rvol = RVOLMetrics(5.0, 10.0, 0.5, False)

    res = engine.evaluate("BTCUSDT", candles, structure, [], obs, [], rvol)
    assert res.decision == ConfluenceDecision.NO_TRADE
    assert any("below minimum required" in r for r in res.rejection_reasons)


def test_confluence_invalid_trend_state_raises_value_error():
    engine = ConfluenceEngine()
    candles = [Candle("BTCUSDT", 100.0, 50000, 51000, 49500, 50800, 10.0)]
    fake_structure = MarketStructureResult("INVALID_TREND", [], [], [])  # type: ignore
    rvol = RVOLMetrics(10.0, 10.0, 1.0, False)

    with pytest.raises(ValueError):
        engine.evaluate("BTCUSDT", candles, fake_structure, [], [], [], rvol)
