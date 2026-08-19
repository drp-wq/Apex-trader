"""
Complete End-to-End System Integration Test for APEX TRADER.
Proves data ingestion -> SMC analysis -> Confluence -> Setup -> Risk Sizing
-> Protective Verification -> Paper Execution -> DB Tracking -> Alerting.
"""
import pytest
from models.domain import Candle, SignalDirection, Provenance
from analysis.market_structure import MarketStructureEngine
from analysis.fvg import FVGEngine
from analysis.order_blocks import OrderBlockEngine
from analysis.liquidity import LiquidityEngine
from analysis.volume_profile import VolumeProfileEngine
from analysis.confluence import ConfluenceEngine, ConfluenceDecision
from analysis.setup_engine import TradeSetupEngine
from risk.deterministic_risk_engine import DeterministicRiskEngine
from scanner.rvol_engine import RVOLEngine
from execution.protection_verifier import ProtectiveOrderVerifier
from execution.execution_engine import ExecutionEngine
from paper.paper_engine import PaperTradingEngine
from database.schema import init_db
from database.performance_tracker import PerformanceTracker
from telegram.telegram_alerts import TelegramNotifier


def test_full_apex_trader_pipeline_e2e(tmp_path):
    # 1. Initialize SQLite Database
    test_db = str(tmp_path / "e2e_apex.db")
    init_db(test_db)
    tracker = PerformanceTracker(db_path=test_db)

    # 2. Initialize Notification & Safety Components
    notifier = TelegramNotifier(enabled=False)
    paper_engine = PaperTradingEngine(initial_balance=500.0, slippage_pct=0.0, fee_pct=0.0004)
    verifier = ProtectiveOrderVerifier()
    exec_engine = ExecutionEngine(paper_exchange=paper_engine, protection_verifier=verifier)

    # 3. Simulate Ingestion: Generate a Bullish SMC Candlestick Pattern
    candles = [
        Candle("BTCUSDT", 100.0, 50000, 50100, 49800, 49900, 10.0, provenance=Provenance.PAPER),
        Candle("BTCUSDT", 200.0, 49900, 50000, 49500, 49600, 10.0, provenance=Provenance.PAPER),
        Candle("BTCUSDT", 300.0, 49600, 50200, 49600, 50100, 10.0, provenance=Provenance.PAPER),
        Candle("BTCUSDT", 400.0, 50100, 51000, 50000, 50900, 10.0, provenance=Provenance.PAPER),
        Candle("BTCUSDT", 500.0, 50900, 50700, 50000, 50200, 10.0, provenance=Provenance.PAPER),
        Candle("BTCUSDT", 600.0, 50200, 52000, 50100, 51800, 80.0, provenance=Provenance.PAPER),
        Candle("BTCUSDT", 700.0, 51800, 52200, 51200, 52000, 30.0, provenance=Provenance.PAPER),
    ]

    # 4. SMC Analysis Engines
    ms_engine = MarketStructureEngine(left_bars=1, right_bars=1)
    fvg_engine = FVGEngine()
    ob_engine = OrderBlockEngine()
    liq_engine = LiquidityEngine(swing_lookback=1)
    vp_engine = VolumeProfileEngine()
    rvol_engine = RVOLEngine()

    structure = ms_engine.analyze(candles)
    fvgs = fvg_engine.get_unmitigated_fvgs(candles)
    obs = ob_engine.get_unmitigated_obs(candles)
    sweeps = liq_engine.detect_sweeps(candles)
    vp = vp_engine.calculate(candles)
    rvol = rvol_engine.calculate([c.volume for c in candles])

    # 5. Confluence Gate Evaluation
    confluence_engine = ConfluenceEngine(min_score=50.0, min_rvol=1.0)
    confluence = confluence_engine.evaluate(
        symbol="BTCUSDT",
        candles=candles,
        structure=structure,
        fvgs=fvgs,
        obs=obs,
        sweeps=sweeps,
        rvol_metrics=rvol,
        volume_profile=vp,
        provenance=Provenance.PAPER
    )
    assert confluence.decision == ConfluenceDecision.TRADE

    # 6. Trade Setup Generation
    setup_engine = TradeSetupEngine()
    setup = setup_engine.generate_setup(confluence)
    assert setup.is_valid is True
    tracker.record_setup(setup)
    notifier.notify_new_setup(setup)

    # 7. Risk Sizing & Paper Order Construction (1% max risk)
    risk_engine = DeterministicRiskEngine(max_account_risk_pct=0.01, min_rr_ratio=2.0)
    risk_res = risk_engine.evaluate_setup(paper_engine.get_balance(), setup)
    assert risk_res.is_valid is True

    order = risk_engine.build_paper_order(setup, risk_res)

    # 8. Protective Verification & Paper Execution Router
    fill = exec_engine.submit_order(order)
    assert fill["status"] == "FILLED"
    assert "BTCUSDT" in paper_engine.positions
    notifier.notify_paper_fill(order.symbol, order.direction, fill["exec_price"], fill["quantity"])

    # 9. Feed Take-Profit Trigger Candle
    target_hit_candle = Candle("BTCUSDT", 500.0, 51000, setup.tp1 + 100.0, 50800, setup.tp1 + 50.0, 20.0)
    closed_trades = paper_engine.on_price_update(target_hit_candle)

    assert len(closed_trades) == 1
    assert closed_trades[0].exit_reason == "TAKE_PROFIT"
    assert closed_trades[0].realized_pnl > 0.0

    # 10. Persist Trade in SQLite Database & Dispatch Alert
    tracker.record_trade(closed_trades[0])
    notifier.notify_trade_closed(closed_trades[0])

    # 11. Verify Database Performance Metrics
    metrics = tracker.get_summary_metrics()
    assert metrics["total_trades"] == 1
    assert metrics["win_rate_pct"] == 100.0
    assert metrics["net_pnl"] > 0.0
