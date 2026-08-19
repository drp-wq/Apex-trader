import pytest
from telegram.telegram_alerts import TelegramNotifier
from models.domain import SignalDirection, Provenance
from analysis.setup_engine import TradeSetup
from paper.paper_engine import PaperTradeRecord


def test_telegram_mock_send():
    notifier = TelegramNotifier(enabled=False)
    # When disabled, should mock dispatch and return True without making network calls
    res = notifier.send_message("Test message")
    assert res is True


def test_telegram_setup_notification_formatting():
    notifier = TelegramNotifier(enabled=False)
    setup = TradeSetup(
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        entry_price=50000.0,
        stop_loss=49500.0,
        tp1=51000.0,
        tp2=51500.0,
        tp3=52500.0,
        rr_tp1=2.0,
        rr_tp2=3.0,
        rr_tp3=5.0,
        risk_distance=500.0,
        score=85.0,
        confidence=0.85,
        reasons=["OB Bullish", "RVOL 2.1"],
        timestamp=1000.0,
        provenance=Provenance.PAPER,
        is_valid=True
    )
    assert notifier.notify_new_setup(setup) is True


def test_telegram_trade_exit_notification():
    notifier = TelegramNotifier(enabled=False)
    record = PaperTradeRecord(
        trade_id="t-1",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        entry_price=50000.0,
        exit_price=51000.0,
        quantity=0.01,
        realized_pnl=10.0,
        fees_paid=0.4,
        entry_time=1000.0,
        exit_time=2000.0,
        exit_reason="TAKE_PROFIT",
        provenance=Provenance.PAPER
    )
    assert notifier.notify_trade_closed(record) is True
    assert notifier.notify_emergency_flatten(2) is True
