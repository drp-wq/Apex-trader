"""
Trade Performance & Safety Event Tracker with SQLite persistence.
"""
import sqlite3
import time
from typing import List, Dict, Any, Optional
from paper.paper_engine import PaperTradeRecord
from analysis.setup_engine import TradeSetup
from config.settings import get_config


class PerformanceTracker:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_config().db_path

    def record_trade(self, trade: PaperTradeRecord) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO paper_trades 
            (trade_id, symbol, direction, entry_price, exit_price, quantity, realized_pnl, fees_paid, entry_time, exit_time, exit_reason, provenance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.trade_id, trade.symbol, trade.direction.value, trade.entry_price, trade.exit_price,
            trade.quantity, trade.realized_pnl, trade.fees_paid, trade.entry_time, trade.exit_time,
            trade.exit_reason, trade.provenance.value
        ))
        conn.commit()
        conn.close()

    def record_setup(self, setup: TradeSetup) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trade_setups
            (symbol, direction, entry_price, stop_loss, tp1, tp2, tp3, score, confidence, timestamp, is_valid, rejection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            setup.symbol, setup.direction.value, setup.entry_price, setup.stop_loss,
            setup.tp1, setup.tp2, setup.tp3, setup.score, setup.confidence, setup.timestamp,
            1 if setup.is_valid else 0, setup.rejection_reason
        ))
        conn.commit()
        conn.close()

    def log_safety_event(self, event_type: str, details: str) -> None:
        cfg = get_config()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO safety_events (event_type, details, timestamp, dry_run, auto_execute)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_type, details, time.time(),
            1 if cfg.safety.DRY_RUN else 0,
            1 if cfg.safety.AUTO_EXECUTE else 0
        ))
        conn.commit()
        conn.close()

    def get_summary_metrics(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT realized_pnl, fees_paid FROM paper_trades")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "gross_pnl": 0.0,
                "net_pnl": 0.0,
                "total_fees": 0.0
            }

        pnls = [r[0] for r in rows]
        fees = sum(r[1] for r in rows)
        wins = [p for p in pnls if p > 0]
        net_pnl = sum(pnls)

        return {
            "total_trades": len(rows),
            "win_rate_pct": round((len(wins) / len(rows)) * 100.0, 2),
            "gross_pnl": round(net_pnl + fees, 4),
            "net_pnl": round(net_pnl, 4),
            "total_fees": round(fees, 4)
        }
