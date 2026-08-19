import pytest
from core.safety import SafetyPolicy, SafetyViolationError
from config.settings import AppConfig, SafetySettings
from execution.execution_engine import ExecutionEngine
from exchanges.paper import PaperExchange
from models.domain import Order, SignalDirection, OrderType, Provenance


def test_live_execution_rejected():
    policy = SafetyPolicy()
    with pytest.raises(SafetyViolationError, match="must be 'PAPER'"):
        policy.verify_order_execution({"provenance": "REAL"})


def test_production_endpoint_rejected():
    policy = SafetyPolicy()
    with pytest.raises(SafetyViolationError, match="Blocked endpoint access"):
        policy.verify_endpoint_url("https://fapi.binance.com/v1/order")


def test_auto_execute_true_rejected():
    unsafe_config = AppConfig(safety=SafetySettings(AUTO_EXECUTE=True))
    policy = SafetyPolicy(config_override=unsafe_config)
    with pytest.raises(SafetyViolationError, match="AUTO_EXECUTE must be False"):
        policy.verify_order_execution({"provenance": "PAPER"})


def test_dry_run_false_rejected():
    unsafe_config = AppConfig(safety=SafetySettings(DRY_RUN=False))
    policy = SafetyPolicy(config_override=unsafe_config)
    with pytest.raises(SafetyViolationError, match="DRY_RUN must be True"):
        policy.verify_order_execution({"provenance": "PAPER"})


def test_production_enabled_rejected():
    unsafe_config = AppConfig(safety=SafetySettings(PRODUCTION_ENABLED=True))
    policy = SafetyPolicy(config_override=unsafe_config)
    with pytest.raises(SafetyViolationError, match="PRODUCTION_ENABLED must be False"):
        policy.verify_order_execution({"provenance": "PAPER"})


def test_missing_safety_config_fails_closed():
    class IncompleteConfig:
        safety = object()

    policy = SafetyPolicy(config_override=IncompleteConfig())
    with pytest.raises(SafetyViolationError):
        policy.verify_order_execution({"provenance": "PAPER"})


def test_paper_trading_allowed():
    policy = SafetyPolicy()
    result = policy.verify_order_execution({"provenance": "PAPER"})
    assert result is True


def test_execution_engine_routing():
    paper = PaperExchange(initial_balance=500.0)
    engine = ExecutionEngine(paper_exchange=paper)
    
    # 500 distance * 0.01 qty = $5.00 risk (exact 1% of $500 balance)
    order = Order(
        order_id="safety-test-01",
        symbol="BTCUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=50000.0,
        quantity=0.01,
        stop_price=49500.0,
        take_profit_price=53000.0,
        provenance=Provenance.PAPER
    )
    
    res = engine.submit_order(order)
    assert res["status"] == "FILLED"
    assert "BTCUSDT" in paper.get_positions()
