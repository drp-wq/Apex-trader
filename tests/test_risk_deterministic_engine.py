import pytest
from risk.deterministic_risk_engine import DeterministicRiskEngine
from models.domain import SignalDirection

def test_risk_evaluation_long_valid():
    engine = DeterministicRiskEngine(max_account_risk_pct=0.01, min_rr_ratio=2.0)
    res = engine.evaluate_order(
        account_balance=500.0,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=115.0,
        direction=SignalDirection.BUY
    )
    assert res.is_valid is True
    assert res.risk_amount_usdt == 5.0  # 1% of $500
    assert res.position_size == 1.0     # $5 risk / $5 stop distance
    assert res.rr_ratio == 3.0

def test_risk_evaluation_sub_min_rr_rejected():
    engine = DeterministicRiskEngine(max_account_risk_pct=0.01, min_rr_ratio=2.0)
    res = engine.evaluate_order(
        account_balance=500.0,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=105.0,  # RR is only 1.0
        direction=SignalDirection.BUY
    )
    assert res.is_valid is False
    assert "below required minimum" in res.rejection_reason

def test_risk_evaluation_invalid_stop_placement():
    engine = DeterministicRiskEngine()
    res = engine.evaluate_order(
        account_balance=500.0,
        entry_price=100.0,
        stop_loss=105.0,  # Long SL above entry
        take_profit=120.0,
        direction=SignalDirection.BUY
    )
    assert res.is_valid is False
    assert "Long SL must be strictly below Entry" in res.rejection_reason

def test_risk_evaluation_max_leverage_cap():
    engine = DeterministicRiskEngine(max_account_risk_pct=0.05, max_leverage=3)
    # 5% of 500 = $25 risk. With $1 stop distance, size would be 25 units ($2500 notional).
    # Max allowed notional with 3x leverage on $500 is $1500 (15 units).
    res = engine.evaluate_order(
        account_balance=500.0,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=105.0,
        direction=SignalDirection.BUY
    )
    assert res.is_valid is True
    assert res.position_size == 15.0  # Capped by 3x leverage

def test_risk_evaluation_zero_balance():
    engine = DeterministicRiskEngine()
    res = engine.evaluate_order(0.0, 100.0, 95.0, 110.0, SignalDirection.BUY)
    assert res.is_valid is False
