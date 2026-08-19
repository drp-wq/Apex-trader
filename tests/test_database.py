import pytest
import os
from database.schema import init_db
from database.performance_tracker import PerformanceTracker
from paper.paper_engine import PaperTradeRecord
from models.domain import SignalDirection, Provenance


def test_sqlite_schema_and_tracker(tmp_path):
    test_db = str(tmp_path / "test_apex.db")
    init_db(test_db)

    tracker = PerformanceTracker(db_path=test_db)
    trade = PaperTradeRecord(
        trade_id="db-t1",
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
    tracker.record_trade(trade)
    tracker.log_safety_event("TEST_EVENT", "Safety check passed")

    summary = tracker.get_summary_metrics()
    assert summary["total_trades"] == 1
    assert summary["win_rate_pct"] == 100.0
    assert summary["net_pnl"] == 10.0
    assert summary["total_fees"] == 0.4
