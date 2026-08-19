"""
Global Configuration & Immutable Safety Defaults for APEX TRADER.
Safety constraints are hardcoded to fail-closed defaults.
"""
from dataclasses import dataclass
from typing import Optional
import os


@dataclass(frozen=True)
class SafetySettings:
    DRY_RUN: bool = True
    AUTO_EXECUTE: bool = False
    PRODUCTION_ENABLED: bool = False
    ALLOW_TESTNET_ORDERS: bool = False
    MAX_ACCOUNT_RISK_PCT: float = 0.01  # Max 1% risk per trade
    MAX_LEVERAGE: int = 5
    MIN_RR_RATIO: float = 2.0
    STALE_DATA_TIMEOUT_SEC: float = 10.0


@dataclass
class AppConfig:
    # Environment & Safety
    safety: SafetySettings = SafetySettings()
    
    # Portfolio Defaults
    initial_paper_balance: float = 500.0
    base_currency: str = "USDT"
    
    # API / Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database
    db_path: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "database",
        "apex_trader.db"
    )
    
    # Binance Futures Public Endpoints (Read-Only)
    binance_fapi_rest_url: str = "https://fapi.binance.com"
    binance_fapi_ws_url: str = "wss://fstream.binance.com/ws"
    
    # Binance Futures Testnet Endpoints
    binance_testnet_rest_url: str = "https://testnet.binancefuture.com"
    binance_testnet_ws_url: str = "wss://stream.binancefuture.com/ws"


def get_config() -> AppConfig:
    """Returns the application configuration with enforced immutable safety constraints."""
    return AppConfig()
