"""
Resilient Binance Futures WebSocket Public Kline Streamer.
Enforces read-only public access with zero credential handling.
"""
import asyncio
import json
import time
import logging
from typing import Callable, Optional, Dict, Any
import websockets
from models.domain import Candle, Provenance
from core.safety import safety_policy, SafetyViolationError

logger = logging.getLogger(__name__)


class BinanceFuturesWSClient:
    """Public read-only WebSocket client for real-time Binance Futures candles."""

    def __init__(
        self,
        symbol: str,
        timeframe: str = "15m",
        on_candle_callback: Optional[Callable[[Candle, bool], None]] = None,
        base_ws_url: str = "wss://fstream.binance.com/ws",
        stale_threshold_sec: float = 30.0
    ):
        self.symbol = symbol.upper()
        self.timeframe = timeframe
        self.on_candle_callback = on_candle_callback
        self.base_ws_url = base_ws_url.rstrip("/")
        self.stale_threshold_sec = stale_threshold_sec

        # Enforce safety gate on WS endpoint
        safety_policy.verify_endpoint_url(self.base_ws_url)

        self.stream_name = f"{self.symbol.lower()}@kline_{self.timeframe}"
        self.ws_url = f"{self.base_ws_url}/{self.stream_name}"
        
        self.is_running: bool = False
        self.last_message_ts: float = 0.0
        self._task: Optional[asyncio.Task] = None

    def parse_kline_payload(self, raw_msg: str) -> Optional[tuple[Candle, bool]]:
        """
        Parses raw Binance WS JSON into a normalized Candle domain object.
        Returns (Candle, is_candle_closed).
        """
        try:
            data = json.loads(raw_msg)
            if "k" not in data:
                return None

            k = data["k"]
            candle = Candle(
                symbol=k.get("s", self.symbol).upper(),
                timestamp=float(k.get("t", 0)) / 1000.0,
                open=float(k.get("o", 0.0)),
                high=float(k.get("h", 0.0)),
                low=float(k.get("l", 0.0)),
                close=float(k.get("c", 0.0)),
                volume=float(k.get("v", 0.0)),
                timeframe=self.timeframe,
                provenance=Provenance.REAL
            )
            is_closed = bool(k.get("x", False))
            return candle, is_closed
        except (ValueError, KeyError, TypeError) as err:
            logger.warning(f"Malformed WS payload received: {err}")
            return None

    def is_data_stale(self) -> bool:
        """Returns True if no message has been received within the stale threshold."""
        if self.last_message_ts == 0.0:
            return True
        return (time.time() - self.last_message_ts) > self.stale_threshold_sec

    async def connect_and_listen(self, reconnect_delay: float = 3.0):
        """Persistent connection loop with automatic reconnect and graceful shutdown."""
        self.is_running = True
        while self.is_running:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                    logger.info(f"Connected to Binance WS stream: {self.stream_name}")
                    while self.is_running:
                        msg = await ws.recv()
                        self.last_message_ts = time.time()
                        parsed = self.parse_kline_payload(msg)
                        if parsed and self.on_candle_callback:
                            candle, is_closed = parsed
                            self.on_candle_callback(candle, is_closed)
            except asyncio.CancelledError:
                break
            except Exception as err:
                if not self.is_running:
                    break
                logger.error(f"WebSocket error: {err}. Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)

    def start(self):
        """Starts WebSocket listener in an asyncio background task."""
        if not self.is_running:
            self._task = asyncio.create_task(self.connect_and_listen())

    async def stop(self):
        """Gracefully stops the WebSocket loop."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
