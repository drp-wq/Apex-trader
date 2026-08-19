import pytest
from models.domain import Candle, Provenance
from replay.replay_engine import ReplayEngine


def test_replay_engine_initialization_and_empty():
    engine = ReplayEngine(initial_balance=500.0)
    metrics = engine.run([])
    assert metrics.total_trades == 0
    assert metrics.ending_balance == 500.0
    assert metrics.win_rate_pct == 0.0


def test_replay_engine_simulation_run():
    engine = ReplayEngine(initial_balance=500.0, min_confluence_score=50.0, min_rvol=1.0)
    candles = []
    base_p = 100.0

    # Generate 40 synthetic bars
    for i in range(40):
        o = base_p + i * 0.5
        h = o + 2.0
        l = o - 1.0
        c = o + 1.0
        candles.append(Candle("BTCUSDT", float(i * 900), o, h, l, c, 100.0 + i, provenance=Provenance.REPLAY))

    metrics = engine.run(candles, lookback_window=10)
    assert metrics.ending_balance >= 0.0
    assert metrics.max_drawdown_pct >= 0.0
