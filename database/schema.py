"""
Deterministic SQLite Schema Initializer for APEX TRADER.
"""
import sqlite3
from config.settings import get_config


def init_db(db_path: str = None) -> None:
    path = db_path or get_config().db_path
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paper_trades (
        trade_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL NOT NULL,
        quantity REAL NOT NULL,
        realized_pnl REAL NOT NULL,
        fees_paid REAL NOT NULL,
        entry_time REAL NOT NULL,
        exit_time REAL NOT NULL,
        exit_reason TEXT NOT NULL,
        provenance TEXT NOT NULL DEFAULT 'PAPER'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_setups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        stop_loss REAL NOT NULL,
        tp1 REAL NOT NULL,
        tp2 REAL NOT NULL,
        tp3 REAL NOT NULL,
        score REAL NOT NULL,
        confidence REAL NOT NULL,
        timestamp REAL NOT NULL,
        is_valid INTEGER NOT NULL,
        rejection_reason TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS safety_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp REAL NOT NULL,
        dry_run INTEGER NOT NULL,
        auto_execute INTEGER NOT NULL
    );
    """)

    conn.commit()
    conn.close()
