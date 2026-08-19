"""
FastAPI Control Plane for APEX TRADER.
Exposes safety monitoring, market metrics, paper trading, and replay endpoints.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time

from core.safety import safety_policy, SafetyViolationError
from paper.paper_engine import PaperTradingEngine
from execution.execution_engine import ExecutionEngine
from execution.emergency_flatten import EmergencyFlatten
from replay.replay_engine import ReplayEngine
from risk.deterministic_risk_engine import DeterministicRiskEngine
from database.schema import init_db
from database.performance_tracker import PerformanceTracker
from models.domain import Order, SignalDirection, OrderType, Provenance, Candle

# Initialize database
init_db()

app = FastAPI(
    title="APEX TRADER API",
    description="Crypto Futures SMC Analysis & Paper Trading Control Plane",
    version="1.0.0"
)

# Enable CORS for iPad / browser dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core singletons
paper_engine = PaperTradingEngine(initial_balance=500.0)
exec_engine = ExecutionEngine(paper_exchange=paper_engine)
emergency_flatten = EmergencyFlatten(paper_engine=paper_engine)
tracker = PerformanceTracker()


class OrderRequest(BaseModel):
    symbol: str
    direction: str  # "BUY" or "SELL"
    price: float
    stop_loss: float
    take_profit: float
    quantity: float


class PriceTick(BaseModel):
    symbol: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


@app.get("/health")
def health():
    return {"status": "ONLINE", "timestamp": time.time()}


@app.get("/safety")
def get_safety():
    """Returns the immutable safety status."""
    return safety_policy.get_safety_status()


@app.get("/paper/account")
def get_paper_account():
    """Returns balance, equity, and position metrics."""
    return paper_engine.get_account_summary()


@app.get("/paper/positions")
def get_paper_positions():
    """Returns all active paper positions."""
    return {
        sym: {
            "symbol": pos.symbol,
            "direction": pos.direction.value,
            "entry_price": pos.entry_price,
            "quantity": pos.quantity,
            "stop_loss": pos.stop_loss,
            "take_profit": pos.take_profit,
            "unrealized_pnl": pos.unrealized_pnl,
            "provenance": pos.provenance.value
        }
        for sym, pos in paper_engine.positions.items()
    }


@app.post("/paper/order")
def submit_paper_order(req: OrderRequest):
    """Submits and verifies a paper order."""
    try:
        direction = SignalDirection.BUY if req.direction.upper() == "BUY" else SignalDirection.SELL
        order = Order(
            order_id=f"api-{int(time.time()*1000)}",
            symbol=req.symbol.upper(),
            direction=direction,
            order_type=OrderType.MARKET,
            price=req.price,
            quantity=req.quantity,
            stop_price=req.stop_loss,
            take_profit_price=req.take_profit,
            provenance=Provenance.PAPER
        )
        res = exec_engine.submit_order(order)
        tracker.log_safety_event("PAPER_ORDER_SUBMITTED", f"{order.symbol} {order.direction.value}")
        return res
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.post("/paper/candle_tick")
def process_candle_tick(tick: PriceTick):
    """Feeds a candle to the paper engine to trigger SL/TP."""
    candle = Candle(
        symbol=tick.symbol.upper(),
        timestamp=tick.timestamp,
        open=tick.open,
        high=tick.high,
        low=tick.low,
        close=tick.close,
        volume=tick.volume,
        provenance=Provenance.PAPER
    )
    closed = paper_engine.on_price_update(candle)
    for record in closed:
        tracker.record_trade(record)
    return {"closed_trades_count": len(closed)}


@app.post("/paper/flatten")
def trigger_emergency_flatten(current_prices: Dict[str, float]):
    """Flattens all open paper positions immediately."""
    try:
        closed = emergency_flatten.flatten_all(current_prices)
        for record in closed:
            tracker.record_trade(record)
        tracker.log_safety_event("EMERGENCY_FLATTEN", f"Liquidated {len(closed)} positions")
        return {"status": "FLATTENED", "liquidated_trades": len(closed)}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.get("/metrics/summary")
def get_performance_summary():
    return tracker.get_summary_metrics()
