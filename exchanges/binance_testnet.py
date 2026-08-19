"""
Isolated Binance Futures Testnet Adapter (Read-Only).
Strictly validates endpoints against Testnet domains and blocks live orders.
"""
from typing import Dict, Any, List, Optional
import requests
from core.safety import safety_policy, SafetyViolationError
from models.domain import Candle, Provenance


class BinanceTestnetAdapter:
    def __init__(
        self,
        rest_url: str = "https://testnet.binancefuture.com",
        ws_url: str = "wss://stream.binancefuture.com/ws"
    ):
        self.rest_url = rest_url.rstrip("/")
        self.ws_url = ws_url.rstrip("/")
        
        # Enforce domain isolation: Must contain 'testnet' or 'binancefuture'
        self._validate_endpoints()

    def _validate_endpoints(self) -> None:
        safety_policy.verify_endpoint_url(self.rest_url)
        safety_policy.verify_endpoint_url(self.ws_url)
        if "testnet.binancefuture.com" not in self.rest_url:
            raise SafetyViolationError(f"Rejected non-testnet REST endpoint: {self.rest_url}")

    def fetch_testnet_server_time(self) -> int:
        """Fetches public Testnet server time (read-only, no credentials)."""
        url = f"{self.rest_url}/fapi/v1/time"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return int(resp.json().get("serverTime", 0))

    def fetch_testnet_klines(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 50
    ) -> List[Candle]:
        """Fetches public testnet candlestick history."""
        url = f"{self.rest_url}/fapi/v1/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        candles: List[Candle] = []
        for k in data:
            candles.append(Candle(
                symbol=symbol.upper(),
                timestamp=float(k[0]) / 1000.0,
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
                timeframe=interval,
                provenance=Provenance.TESTNET
            ))
        return candles

    def place_order(self, *args, **kwargs) -> None:
        """Hard barrier: Live/Testnet automated order placement is permanently disabled."""
        raise SafetyViolationError("Execution Barrier: Direct order execution via Testnet adapter is disabled.")
