import pytest
from models.domain import SignalDirection, Provenance
from analysis.confluence import ConfluenceResult, ConfluenceDecision
from analysis.setup_engine import TradeSetupEngine


def test_setup_engine_bullish_targets():
    engine = TradeSetupEngine(tp1_rr_multiplier=2.0, tp2_rr_multiplier=3.0, tp3_rr_multiplier=5.0)
    confluence = ConfluenceResult(
        decision=ConfluenceDecision.TRADE,
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        score=85.0,
        reasons=["Trend aligned", "OB present"],
        rejection_reasons=[],
        entry_zone_high=100.0,
        entry_zone_low=100.0,
        invalidation_price=95.0,  # 5 point risk
        confidence=0.85,
        timestamp=1000.0,
        provenance=Provenance.PAPER
    )
    setup = engine.generate_setup(confluence)
    assert setup.is_valid is True
    assert setup.entry_price == 100.0
    assert setup.stop_loss == 95.0
    assert setup.risk_distance == 5.0
    assert setup.tp1 == 110.0  # 100 + (5 * 2)
    assert setup.tp2 == 115.0  # 100 + (5 * 3)
    assert setup.tp3 == 125.0  # 100 + (5 * 5)


def test_setup_engine_bearish_targets():
    engine = TradeSetupEngine()
    confluence = ConfluenceResult(
        decision=ConfluenceDecision.TRADE,
        symbol="ETHUSDT",
        direction=SignalDirection.SELL,
        score=90.0,
        reasons=["Bearish BOS", "FVG active"],
        rejection_reasons=[],
        entry_zone_high=2000.0,
        entry_zone_low=2000.0,
        invalidation_price=2050.0,  # 50 point risk
        confidence=0.90,
        timestamp=1000.0,
        provenance=Provenance.PAPER
    )
    setup = engine.generate_setup(confluence)
    assert setup.is_valid is True
    assert setup.entry_price == 2000.0
    assert setup.stop_loss == 2050.0
    assert setup.risk_distance == 50.0
    assert setup.tp1 == 1900.0  # 2000 - (50 * 2)
    assert setup.tp2 == 1850.0  # 2000 - (50 * 3)
    assert setup.tp3 == 1750.0  # 2000 - (50 * 5)


def test_setup_engine_rejects_no_trade():
    engine = TradeSetupEngine()
    confluence = ConfluenceResult(
        decision=ConfluenceDecision.NO_TRADE,
        symbol="SOLUSDT",
        direction=SignalDirection.BUY,
        score=40.0,
        reasons=[],
        rejection_reasons=["RVOL too low"],
        entry_zone_high=150.0,
        entry_zone_low=150.0,
        invalidation_price=145.0,
        confidence=0.40,
        timestamp=1000.0,
        provenance=Provenance.PAPER
    )
    setup = engine.generate_setup(confluence)
    assert setup.is_valid is False
    assert "NO_TRADE" in setup.rejection_reason


def test_setup_engine_invalid_sl_placement():
    engine = TradeSetupEngine()
    # Long trade with SL above entry
    confluence = ConfluenceResult(
        decision=ConfluenceDecision.TRADE,
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        score=80.0,
        reasons=[],
        rejection_reasons=[],
        entry_zone_high=100.0,
        entry_zone_low=100.0,
        invalidation_price=105.0,
        confidence=0.80,
        timestamp=1000.0,
        provenance=Provenance.PAPER
    )
    setup = engine.generate_setup(confluence)
    assert setup.is_valid is False
    assert "Long stop-loss must be strictly below" in setup.rejection_reason
