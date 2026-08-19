import pytest
from exchanges.binance_testnet import BinanceTestnetAdapter
from core.safety import SafetyViolationError


def test_testnet_adapter_endpoint_validation():
    adapter = BinanceTestnetAdapter()
    assert "testnet.binancefuture.com" in adapter.rest_url


def test_testnet_adapter_rejects_production_endpoint():
    with pytest.raises(SafetyViolationError):
        BinanceTestnetAdapter(rest_url="https://fapi.binance.com")


def test_testnet_adapter_order_placement_hard_barrier():
    adapter = BinanceTestnetAdapter()
    with pytest.raises(SafetyViolationError, match="Direct order execution via Testnet adapter is disabled"):
        adapter.place_order(symbol="BTCUSDT", side="BUY", quantity=0.01)
