"""
Deterministic Historical Replay & Backtest Engine for APEX TRADER.
Feeds candles chronologically through the SMC pipeline and paper executor.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional

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
from paper.paper_engine import PaperTradingEngine, PaperTradeRecord


@dataclass(frozen=True)
class ReplayMetrics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    gross_profit: float
    gross_loss: float
    net_pnl: float
    profit_factor: float
    max_drawdown_pct: float
    ending_balance: float


class ReplayEngine:
    def __init__(
        self,
        initial_balance: float = 500.0,
        min_confluence_score: float = 70.0,
        min_rvol: float = 1.2
    ):
        self.initial_balance = initial_balance
        self.paper_engine = PaperTradingEngine(initial_balance=initial_balance, slippage_pct=0.0005, fee_pct=0.0004)
        self.ms_engine = MarketStructureEngine(left_bars=2, right_bars=2)
        self.fvg_engine = FVGEngine()
        self.ob_engine = OrderBlockEngine()
        self.liq_engine = LiquidityEngine()
        self.vp_engine = VolumeProfileEngine()
        self.confluence_engine = ConfluenceEngine(min_score=min_confluence_score, min_rvol=min_rvol)
        self.setup_engine = TradeSetupEngine()
        self.risk_engine = DeterministicRiskEngine(max_account_risk_pct=0.01, min_rr_ratio=2.0)
        self.rvol_engine = RVOLEngine()

    def run(self, historical_candles: List[Candle], lookback_window: int = 30) -> ReplayMetrics:
        """
        Steps through historical candle sequence bar-by-bar.
        """
        if len(historical_candles) < lookback_window:
            return self._calculate_metrics([])

        peak_balance = self.initial_balance
        max_drawdown_pct = 0.0

        for i in range(lookback_window, len(historical_candles)):
            current_bar = historical_candles[i]
            window = historical_candles[:i]

            # 1. Update open positions against incoming price bar
            self.paper_engine.on_price_update(current_bar)

            # Track peak equity and drawdown
            curr_equity = self.paper_engine.balance
            if curr_equity > peak_balance:
                peak_balance = curr_equity
            dd_pct = ((peak_balance - curr_equity) / peak_balance) * 100.0 if peak_balance > 0 else 0.0
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct

            # Skip new entry if position already open for this symbol
            if current_bar.symbol in self.paper_engine.positions:
                continue

            # 2. Run analysis suite
            structure = self.ms_engine.analyze(window)
            fvgs = self.fvg_engine.get_unmitigated_fvgs(window)
            obs = self.ob_engine.get_unmitigated_obs(window)
            sweeps = self.liq_engine.detect_sweeps(window)
            vp = self.vp_engine.calculate(window[-20:])
            vol_history = [c.volume for c in window]
            rvol = self.rvol_engine.calculate(vol_history)

            # 3. Confluence decision
            confluence = self.confluence_engine.evaluate(
                symbol=current_bar.symbol,
                candles=window,
                structure=structure,
                fvgs=fvgs,
                obs=obs,
                sweeps=sweeps,
                rvol_metrics=rvol,
                volume_profile=vp,
                provenance=Provenance.REPLAY
            )

            if confluence.decision != ConfluenceDecision.TRADE:
                continue

            # 4. Generate Setup
            setup = self.setup_engine.generate_setup(confluence)
            if not setup.is_valid:
                continue

            # 5. Risk sizing
            risk_res = self.risk_engine.evaluate_setup(self.paper_engine.balance, setup)
            if not risk_res.is_valid:
                continue

            # 6. Execute paper order
            order = self.risk_engine.build_paper_order(setup, risk_res)
            order.provenance = Provenance.PAPER  # Enforce safety gate
            self.paper_engine.execute_order(order, tp2=setup.tp2, tp3=setup.tp3)

        return self._calculate_metrics(self.paper_engine.trade_history, max_drawdown_pct)

    def _calculate_metrics(self, trades: List[PaperTradeRecord], max_dd_pct: float = 0.0) -> ReplayMetrics:
        total = len(trades)
        if total == 0:
            return ReplayMetrics(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, max_dd_pct, self.paper_engine.balance)

        wins = [t for t in trades if t.realized_pnl > 0]
        losses = [t for t in trades if t.realized_pnl <= 0]
        gross_profit = sum(t.realized_pnl for t in wins)
        gross_loss = abs(sum(t.realized_pnl for t in losses))
        net_pnl = round(gross_profit - gross_loss, 4)
        win_rate = round((len(wins) / total) * 100.0, 2)
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        return ReplayMetrics(
            total_trades=total,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=win_rate,
            gross_profit=round(gross_profit, 4),
            gross_loss=round(gross_loss, 4),
            net_pnl=net_pnl,
            profit_factor=profit_factor,
            max_drawdown_pct=round(max_dd_pct, 2),
            ending_balance=round(self.paper_engine.balance, 4)
        )
