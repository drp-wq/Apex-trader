import pytest
from models.domain import (
    Candle,
    Order,
    SignalDirection,
    OrderType,
    OrderStatus,
    Provenance,
)
from paper.paper_engine import PaperTradingEngine


def test_paper_engine_execution_and_fees():
    engine = PaperTradingEngine(initial_balance=500.0, slippage_pct=0.001, fee_pct=0.0005)
    order = Order(
        order_id="test-ord-1",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.01,
        stop_price=49000.0,
        take_profit_price=52000.0,
        provenance=Provenance.PAPER,
        timestamp=1000.0
    )
    result = engine.execute_order(order)
    assert result["status"] == "FILLED"
    assert "BTCUSDT" in engine.positions
    pos = engine.positions["BTCUSDT"]
    # 50000 * 1.001 = 50050.0 entry with slippage
    assert pos.entry_price == 50050.0
    assert engine.balance < 500.0  # Entry fee deducted


def test_paper_engine_stop_loss_trigger():
    engine = PaperTradingEngine(initial_balance=500.0, slippage_pct=0.0, fee_pct=0.0)
    order = Order(
        order_id="test-ord-2",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.01,
        stop_price=49000.0,
        take_profit_price=53000.0,
        provenance=Provenance.PAPER,
        timestamp=1000.0
    )
    engine.execute_order(order)

    # Candle dipping to 48900 triggers SL @ 49000
    trigger_candle = Candle("BTCUSDT", 2000.0, 49500, 49600, 48900, 49200, 10.0)
    closed = engine.on_price_update(trigger_candle)

    assert len(closed) == 1
    assert closed[0].exit_reason == "STOP_LOSS"
    assert closed[0].exit_price == 49000.0
    assert closed[0].realized_pnl == -10.0  # (49000 - 50000) * 0.01
    assert "BTCUSDT" not in engine.positions
    assert len(engine.trade_history) == 1


def test_paper_engine_take_profit_trigger():
    engine = PaperTradingEngine(initial_balance=500.0, slippage_pct=0.0, fee_pct=0.0)
    order = Order(
        order_id="test-ord-3",
        symbol="ETHUSDT",
        direction=SignalDirection.SELL,
        order_type=OrderType.MARKET,
        price=3000.0,
        quantity=0.1,
        stop_price=3100.0,
        take_profit_price=2800.0,
        provenance=Provenance.PAPER,
        timestamp=1000.0
    )
    engine.execute_order(order)

    # Candle dropping to 2750 triggers Short TP @ 2800
    trigger_candle = Candle("ETHUSDT", 2000.0, 2900, 2950, 2750, 2780, 50.0)
    closed = engine.on_price_update(trigger_candle)

    assert len(closed) == 1
    assert closed[0].exit_reason == "TAKE_PROFIT"
    assert closed[0].exit_price == 2800.0
    assert closed[0].realized_pnl == 20.0  # (3000 - 2800) * 0.1
    assert "ETHUSDT" not in engine.positions


def test_paper_engine_trailing_stop():
    engine = PaperTradingEngine(initial_balance=500.0, slippage_pct=0.0, fee_pct=0.0)
    order = Order(
        order_id="test-ord-4",
        symbol="SOLUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=100.0,
        quantity=1.0,
        stop_price=90.0,
        take_profit_price=150.0,
        provenance=Provenance.PAPER,
        timestamp=1000.0
    )
    # 5 point trailing distance
    engine.execute_order(order, trailing_stop_distance=5.0)

    # Price pushes up to 120 -> SL should ratchet up to 120 - 5 = 115
    up_candle = Candle("SOLUSDT", 2000.0, 105, 120, 104, 119, 10.0)
    engine.on_price_update(up_candle)
    assert engine.positions["SOLUSDT"].stop_loss == 115.0

    # Price drops to 114 -> Hits ratcheted trailing SL
    down_candle = Candle("SOLUSDT", 3000.0, 118, 118, 114, 116, 10.0)
    closed = engine.on_price_update(down_candle)
    assert len(closed) == 1
    assert closed[0].exit_reason == "STOP_LOSS"
    assert closed[0].exit_price == 115.0
    assert closed[0].realized_pnl == 15.0  # (115 - 100) * 1.0
