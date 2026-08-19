import pytest
from models.domain import SignalDirection, Provenance, OrderStatus
from analysis.setup_engine import TradeSetup
from risk.deterministic_risk_engine import DeterministicRiskEngine, RiskViolationError


def test_evaluate_valid_setup_sizing():
    engine = DeterministicRiskEngine(max_account_risk_pct=0.01, min_rr_ratio=2.0)
    setup = TradeSetup(
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        entry_price=50000.0,
        stop_loss=49500.0,  # $500 risk distance (1%)
        tp1=51000.0,        # 1:2 RR
        tp2=51500.0,
        tp3=52500.0,
        rr_tp1=2.0,
        rr_tp2=3.0,
        rr_tp3=5.0,
        risk_distance=500.0,
        score=85.0,
        confidence=0.85,
        reasons=["Valid OB"],
        timestamp=1000.0,
        provenance=Provenance.PAPER,
        is_valid=True
    )
    # $500 balance -> 1% risk = $5 USDT
    # Size = $5 / $500 = 0.01 BTC ($500 notional)
    risk_res = engine.evaluate_setup(500.0, setup)
    assert risk_res.is_valid is True
    assert risk_res.risk_amount_usdt == 5.0
    assert risk_res.position_size == 0.01
    assert risk_res.notional_value == 500.0
    assert risk_res.rr_ratio == 2.0


def test_evaluate_invalid_setup_rejection():
    engine = DeterministicRiskEngine()
    invalid_setup = TradeSetup(
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        entry_price=0.0,
        stop_loss=0.0,
        tp1=0.0,
        tp2=0.0,
        tp3=0.0,
        rr_tp1=0.0,
        rr_tp2=0.0,
        rr_tp3=0.0,
        risk_distance=0.0,
        score=0.0,
        confidence=0.0,
        reasons=[],
        timestamp=1000.0,
        provenance=Provenance.PAPER,
        is_valid=False,
        rejection_reason="Confluence failed"
    )
    risk_res = engine.evaluate_setup(500.0, invalid_setup)
    assert risk_res.is_valid is False
    assert "Invalid TradeSetup" in risk_res.rejection_reason


def test_build_paper_order_workflow():
    engine = DeterministicRiskEngine()
    setup = TradeSetup(
        symbol="ETHUSDT",
        direction=SignalDirection.BUY,
        entry_price=3000.0,
        stop_loss=2950.0,  # $50 risk distance
        tp1=3100.0,
        tp2=3150.0,
        tp3=3250.0,
        rr_tp1=2.0,
        rr_tp2=3.0,
        rr_tp3=5.0,
        risk_distance=50.0,
        score=80.0,
        confidence=0.8,
        reasons=["FVG Bounce"],
        timestamp=1000.0,
        provenance=Provenance.PAPER,
        is_valid=True
    )
    risk_res = engine.evaluate_setup(1000.0, setup)
    assert risk_res.is_valid is True

    order = engine.build_paper_order(setup, risk_res)
    assert order.symbol == "ETHUSDT"
    assert order.direction == SignalDirection.BUY
    assert order.price == 3000.0
    assert order.stop_price == 2950.0
    assert order.take_profit_price == 3100.0
    assert order.provenance == Provenance.PAPER
    assert order.status == OrderStatus.NEW


def test_build_order_from_invalid_risk_raises():
    engine = DeterministicRiskEngine()
    setup = TradeSetup(
        symbol="ETHUSDT",
        direction=SignalDirection.BUY,
        entry_price=3000.0,
        stop_loss=3050.0,  # Invalid SL
        tp1=3200.0,
        tp2=3300.0,
        tp3=3500.0,
        rr_tp1=2.0,
        rr_tp2=3.0,
        rr_tp3=5.0,
        risk_distance=50.0,
        score=80.0,
        confidence=0.8,
        reasons=[],
        timestamp=1000.0,
        provenance=Provenance.PAPER,
        is_valid=True
    )
    risk_res = engine.evaluate_setup(500.0, setup)
    assert risk_res.is_valid is False
    with pytest.raises(RiskViolationError):
        engine.build_paper_order(setup, risk_res)
