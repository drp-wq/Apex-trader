from models.domain import Candle, Order, Position, Provenance, SignalDirection, OrderType
from exchanges.paper import PaperExchange
from config.settings import get_config

def test_domain_models():
    candle = Candle(
        symbol="BTCUSDT",
        timestamp=1700000000.0,
        open=50000.0,
        high=51000.0,
        low=49500.0,
        close=50500.0,
        volume=10.5,
        provenance=Provenance.PAPER
    )
    assert candle.symbol == "BTCUSDT"
    assert candle.high >= candle.low

def test_paper_exchange_balance():
    config = get_config()
    paper = PaperExchange(initial_balance=config.initial_paper_balance)
    assert paper.get_balance() == 500.0

def test_safety_defaults():
    config = get_config()
    assert config.safety.DRY_RUN is True
    assert config.safety.AUTO_EXECUTE is False
    assert config.safety.PRODUCTION_ENABLED is False

def test_immutable_risk():
    config = get_config()
    assert config.safety.MAX_ACCOUNT_RISK_PCT == 0.01

def test_paper_lifecycle():
    paper = PaperExchange(initial_balance=1000.0)
    order = Order(
        order_id="test-1",
        symbol="ETHUSDT",
        direction=SignalDirection.BUY,
        order_type=OrderType.MARKET,
        price=3000.0,
        quantity=0.1,
        stop_price=2900.0,
        take_profit_price=3200.0,
        provenance=Provenance.PAPER
    )
    res = paper.create_order(order)
    assert res["status"] == "FILLED"
    assert "ETHUSDT" in paper.get_positions()
