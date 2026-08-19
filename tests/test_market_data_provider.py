import pytest
from models.domain import Candle, Provenance
from market_data.provider import InMemoryMarketDataProvider, BinancePublicRestProvider
from core.safety import SafetyViolationError


def test_in_memory_provider_push_and_fetch():
    provider = InMemoryMarketDataProvider(provenance=Provenance.PAPER)
    
    c1 = Candle("BTCUSDT", 100.0, 50000.0, 50500.0, 49800.0, 50200.0, 10.0, timeframe="15m")
    c2 = Candle("BTCUSDT", 200.0, 50200.0, 50800.0, 50100.0, 50700.0, 15.0, timeframe="15m")
    
    provider.push_candles([c1, c2])
    
    history = provider.get_historical_candles("BTCUSDT", timeframe="15m", limit=10)
    assert len(history) == 2
    assert history[0].timestamp == 100.0
    assert history[1].timestamp == 200.0
    assert history[0].provenance == Provenance.PAPER
    
    latest = provider.get_latest_candle("BTCUSDT", timeframe="15m")
    assert latest is not None
    assert latest.close == 50700.0


def test_in_memory_provider_sorting():
    provider = InMemoryMarketDataProvider(provenance=Provenance.REPLAY)
    
    c_late = Candle("ETHUSDT", 300.0, 3000.0, 3100.0, 2990.0, 3050.0, 5.0, timeframe="1h")
    c_early = Candle("ETHUSDT", 100.0, 2900.0, 3000.0, 2890.0, 2950.0, 4.0, timeframe="1h")
    
    # Push out of order
    provider.push_candle(c_late)
    provider.push_candle(c_early)
    
    history = provider.get_historical_candles("ETHUSDT", timeframe="1h")
    assert len(history) == 2
    assert history[0].timestamp == 100.0
    assert history[1].timestamp == 300.0
    assert history[0].provenance == Provenance.REPLAY


def test_in_memory_provider_empty():
    provider = InMemoryMarketDataProvider()
    assert provider.get_historical_candles("SOLUSDT") == []
    assert provider.get_latest_candle("SOLUSDT") is None


def test_rest_provider_blocked_unsafe_url():
    with pytest.raises(SafetyViolationError):
        BinancePublicRestProvider(base_url="https://api.binance.com")
