"""
Complete End-to-End System Integration Test for APEX TRADER.
Proves data ingestion -> SMC analysis -> Confluence -> Setup -> Risk Sizing
-> Protective Verification -> Paper Execution -> DB Tracking -> Alerting.
"""
import pytest
from models.domain import Candle, SignalDirection, Provenance, TrendState
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
    # 
    # FIXTURE DESIGN:
    # This sequence creates a deterministic bullish setup with:
    # - 8 candles to establish swing structure (needs 2+ swings for trend detection)
    # - Higher highs and higher lows pattern (bullish trend confirmation)
    # - Strong bullish displacement bar (candle 3: open 49800 -> close 51200, body=1400)
    # - Bullish Fair Value Gap between candles 2-3-4: [50100, 50600] unmitigated
    # - Volume: 10,10,10,60,15,15,15,20 → RVOL on last bar = 20/avg(15,15,15) ≈ 1.33 >= 1.0
    # - No directional breaks, only swing structure (avoids extra BOS/CHOCH logic)
    #
    candles = [
        # Candle 0: Base (low=49500, high=50000)
        Candle("BTCUSDT", 100.0, 49700, 50000, 49500, 49800, 10.0, provenance=Provenance.PAPER),
        
        # Candle 1: Higher low (low=49800, high=50100) — establishes swing low #0
        Candle("BTCUSDT", 200.0, 49900, 50100, 49800, 49950, 10.0, provenance=Provenance.PAPER),
        
        # Candle 2: Base for OB, still rising (low=49800, high=50400)
        Candle("BTCUSDT", 300.0, 50000, 50400, 49800, 50200, 10.0, provenance=Provenance.PAPER),
        
        # Candle 3: STRONG BULLISH DISPLACEMENT (bearish then massive bullish)
        # close < open (49800 < 51200 qualifies as "bullish" despite low being same)
        # Actually open=49800, close=51200 → close > open ✓
        # high=51500, low=49600 (encompasses prior range)
        # volume=60 (expansion from avg of ~10)
        # Triggers: bullish OB at candle 2 (low=49800, high=50400)
        Candle("BTCUSDT", 400.0, 49800, 51500, 49600, 51200, 60.0, provenance=Provenance.PAPER),
        
        # Candle 4: Creates bullish FVG [50100, 50600]
        # c2.low=49800, c3.high=51500, c4.low=50600
        # FVG detected: c2.low > c0.high, which is candle[2].low > candle[0].high
        # Let me recompute: i=4, c0=candle[2], c1=candle[3], c2=candle[4]
        # Bullish FVG if c2.low > c0.high: 50600 > 50400 ✓
        # Gap is [50400, 50600], unmitigated if no post candle.low <= 50400
        Candle("BTCUSDT", 500.0, 51200, 51400, 50600, 51300, 15.0, provenance=Provenance.PAPER),
        
        # Candle 5: Higher high, higher low (bullish continuation, no FVG mitigation)
        Candle("BTCUSDT", 600.0, 51300, 51600, 50900, 51500, 15.0, provenance=Provenance.PAPER),
        
        # Candle 6: Maintains structure (swing high candidate)
        Candle("BTCUSDT", 700.0, 51500, 51800, 51000, 51200, 15.0, provenance=Provenance.PAPER),
        
        # Candle 7: Final bar, volume expansion for RVOL
        # volume=20 > avg of prior(15,15,15) → RVOL ≈ 1.33 >= 1.0
        Candle("BTCUSDT", 800.0, 51200, 51900, 51100, 51800, 20.0, provenance=Provenance.PAPER),
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

    # 5. Validate E2E Fixture Produces Expected Structure
    assert structure.trend == TrendState.BULLISH, \
        f"Expected BULLISH trend, got {structure.trend}. Swings: {len(structure.swing_highs)} high, {len(structure.swing_lows)} low"
    assert rvol.rvol >= 1.0, \
        f"Expected RVOL >= 1.0, got {rvol.rvol} (current_vol={rvol.current_volume}, baseline={rvol.baseline_average_volume})"
    assert fvgs or obs, \
        f"Expected unmitigated FVGs or OBs, got {len(fvgs)} FVGs and {len(obs)} OBs"

    # 6. Confluence Gate Evaluation
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
    assert confluence.decision == ConfluenceDecision.TRADE, \
        f"Expected TRADE, got {confluence.decision}. Rejection reasons: {confluence.rejection_reasons}"

    # 7. Trade Setup Generation
    setup_engine = TradeSetupEngine()
    setup = setup_engine.generate_setup(confluence)
    assert setup.is_valid is True
    tracker.record_setup(setup)
    notifier.notify_new_setup(setup)

    # 8. Risk Sizing & Paper Order Construction (1% max risk)
    risk_engine = DeterministicRiskEngine(max_account_risk_pct=0.01, min_rr_ratio=2.0)
    risk_res = risk_engine.evaluate_setup(paper_engine.get_balance(), setup)
    assert risk_res.is_valid is True

    order = risk_engine.build_paper_order(setup, risk_res)

    # 9. Protective Verification & Paper Execution Router
    fill = exec_engine.submit_order(order)
    assert fill["status"] == "FILLED"
    assert "BTCUSDT" in paper_engine.positions
    notifier.notify_paper_fill(order.symbol, order.direction, fill["exec_price"], fill["quantity"])

    # 10. Feed Take-Profit Trigger Candle
    target_hit_candle = Candle(
        "BTCUSDT",
        900.0,
        51800.0,
        max(51800.0, setup.tp1 + 100.0),
        51700.0,
        setup.tp1 + 50.0,
        20.0,
    )
    closed_trades = paper_engine.on_price_update(target_hit_candle)

    assert len(closed_trades) == 1
    assert closed_trades[0].exit_reason == "TAKE_PROFIT"
    assert closed_trades[0].realized_pnl > 0.0

    # 11. Persist Trade in SQLite Database & Dispatch Alert
    tracker.record_trade(closed_trades[0])
    notifier.notify_trade_closed(closed_trades[0])

    # 12. Verify Database Performance Metrics
    metrics = tracker.get_summary_metrics()
    assert metrics["total_trades"] == 1
    assert metrics["win_rate_pct"] == 100.0
    assert metrics["net_pnl"] > 0.0
