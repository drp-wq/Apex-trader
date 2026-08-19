import pytest
from models.domain import Order, SignalDirection, OrderType, Provenance
from paper.paper_engine import PaperTradingEngine
from execution.emergency_flatten import EmergencyFlatten


def test_emergency_flatten_closes_all_positions():
    paper = PaperTradingEngine(initial_balance=500.0, slippage_pct=0.0, fee_pct=0.0)
    order1 = Order("o-1", "BTCUSDT", SignalDirection.BUY, OrderType.MARKET, 50000.0, 0.01, 49500.0, 51000.0, provenance=Provenance.PAPER)
    order2 = Order("o-2", "ETHUSDT", SignalDirection.SELL, OrderType.MARKET, 3000.0, 0.1, 3050.0, 2900.0, provenance=Provenance.PAPER)

    paper.execute_order(order1)
    paper.execute_order(order2)
    assert len(paper.positions) == 2

    flatten = EmergencyFlatten(paper_engine=paper)
    records = flatten.flatten_all(current_prices={"BTCUSDT": 50200.0, "ETHUSDT": 2980.0})

    assert len(records) == 2
    assert len(paper.positions) == 0
    assert all(r.exit_reason == "EMERGENCY_FLATTEN" for r in records)


def test_emergency_flatten_order_cancellation():
    paper = PaperTradingEngine()
    flatten = EmergencyFlatten(paper_engine=paper)
    paper.order_book["ord-1"] = Order("ord-1", "SOLUSDT", SignalDirection.BUY, OrderType.LIMIT, 100.0, 1.0)
    assert len(paper.order_book) == 1
    cancelled = flatten.cancel_all_orders()
    assert cancelled == 1
    assert len(paper.order_book) == 0
