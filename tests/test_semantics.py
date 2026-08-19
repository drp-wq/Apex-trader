import pytest
from models.domain import Candle, Provenance

def test_price_validation():
    with pytest.raises(ValueError):
        Candle("BTCUSDT", 1700000000.0, 50000.0, 48000.0, 51000.0, 50500.0, 10.0)

def test_timestamp_ordering():
    with pytest.raises(ValueError):
        Candle("BTCUSDT", -1.0, 50000.0, 51000.0, 49000.0, 50500.0, 10.0)

def test_symbol_normalization():
    c = Candle("btcusdt".upper(), 1700000000.0, 50000.0, 51000.0, 49000.0, 50500.0, 10.0)
    assert c.symbol == "BTCUSDT"

def test_invalid_inputs():
    with pytest.raises(ValueError):
        Candle("BTCUSDT", 1700000000.0, -500.0, 51000.0, 49000.0, 50500.0, 10.0)
