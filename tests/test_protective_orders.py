import pytest
from models.domain import Order, SignalDirection, OrderType, Provenance
from execution.protection_verifier import ProtectiveOrderVerifier, ProtectiveOrderViolationError
from execution.execution_engine import ExecutionEngine
from exchanges.paper import PaperExchange


def test_protective_order_missing_stop_loss():
    verifier = ProtectiveOrderVerifier()
    order = Order(
        order_id="p-1",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.01,
        stop_price=None,  # Missing Stop
        take_profit_price=52000.0,
        provenance=Provenance.PAPER
    )
    res = verifier.verify(order, account_balance=500.0)
    assert res.is_valid is False
    assert "Missing mandatory Stop-Loss" in res.rejection_reason


def test_protective_order_missing_take_profit():
    verifier = ProtectiveOrderVerifier()
    order = Order(
        order_id="p-2",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.01,
        stop_price=49000.0,
        take_profit_price=None,  # Missing TP
        provenance=Provenance.PAPER
    )
    res = verifier.verify(order, account_balance=500.0)
    assert res.is_valid is False
    assert "Missing mandatory Take-Profit" in res.rejection_reason


def test_protective_order_invalid_long_sl():
    verifier = ProtectiveOrderVerifier()
    order = Order(
        order_id="p-3",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.01,
        stop_price=51000.0,  # Long SL above entry
        take_profit_price=53000.0,
        provenance=Provenance.PAPER
    )
    res = verifier.verify(order, account_balance=500.0)
    assert res.is_valid is False
    assert "Long Stop-Loss" in res.rejection_reason


def test_protective_order_exceeds_max_risk():
    verifier = ProtectiveOrderVerifier()
    # 500 balance -> max 1% = $5 USDT risk
    # Risk distance $1000 * 0.02 qty = $20 risk (exceeds $5)
    order = Order(
        order_id="p-4",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.02,
        stop_price=49000.0,
        take_profit_price=53000.0,
        provenance=Provenance.PAPER
    )
    res = verifier.verify(order, account_balance=500.0)
    assert res.is_valid is False
    assert "exceeds maximum allowed" in res.rejection_reason


def test_protective_order_valid_passes():
    verifier = ProtectiveOrderVerifier()
    # Risk distance $500 * 0.01 qty = $5 risk (1% of 500)
    order = Order(
        order_id="p-5",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.01,
        stop_price=49500.0,
        take_profit_price=51500.0,
        provenance=Provenance.PAPER
    )
    res = verifier.verify(order, account_balance=500.0)
    assert res.is_valid is True
    assert res.risk_amount == 5.0
    assert res.risk_pct == 1.0


def test_execution_engine_rejects_unprotected_order():
    paper = PaperExchange(initial_balance=500.0)
    engine = ExecutionEngine(paper_exchange=paper)
    
    unprotected_order = Order(
        order_id="p-6",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.01,
        stop_price=None,  # No SL
        take_profit_price=52000.0,
        provenance=Provenance.PAPER
    )
    with pytest.raises(ProtectiveOrderViolationError):
        engine.submit_order(unprotected_order)
