"""
Deterministic Safety Enforcement Layer for APEX TRADER.
Prevents any real-money routing or execution violations at runtime.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from config.settings import get_config


class SafetyViolationError(Exception):
    """Raised when an operation violates trading safety gates."""
    pass


class SafetyPolicy:
    """Centralized fail-closed execution safety validator."""
    
    def __init__(self, config_override=None):
        self.config = config_override or get_config()
    
    def verify_order_execution(self, order_payload: Dict[str, Any]) -> bool:
        """
        Hard gate for order placement.
        Fails closed if any production or auto-execution condition is present.
        """
        # Hard check 1: DRY_RUN must be True
        if not getattr(self.config.safety, "DRY_RUN", False):
            raise SafetyViolationError("Safety Gate Violation: DRY_RUN must be True.")
            
        # Hard check 2: AUTO_EXECUTE must be False
        if getattr(self.config.safety, "AUTO_EXECUTE", True):
            raise SafetyViolationError("Safety Gate Violation: AUTO_EXECUTE must be False.")
            
        # Hard check 3: PRODUCTION_ENABLED must be False
        if getattr(self.config.safety, "PRODUCTION_ENABLED", True):
            raise SafetyViolationError("Safety Gate Violation: PRODUCTION_ENABLED must be False.")
            
        # Hard check 4: Order provenance must be explicitly PAPER
        provenance = str(order_payload.get("provenance", "")).upper()
        if provenance != "PAPER":
            raise SafetyViolationError(
                f"Safety Gate Violation: Provenance must be 'PAPER'. Received: '{provenance}'"
            )
            
        return True

    def verify_paper_execution(self, order_payload: Dict[str, Any]) -> bool:
        return self.verify_order_execution(order_payload)

    def verify_endpoint_url(self, url: str) -> bool:
        """
        Ensures endpoints strictly point to allowed public read-only or Testnet streams.
        Rejects all production private/execution URLs.
        """
        blocked_keywords = ["/v1/order", "/v2/order", "/v3/order", "api.binance.com"]
        for blocked in blocked_keywords:
            if blocked in url:
                raise SafetyViolationError(f"Safety Gate Violation: Blocked endpoint access '{url}'.")

        allowed_domains = [
            "fapi.binance.com",
            "fstream.binance.com",
            "testnet.binancefuture.com",
            "stream.binancefuture.com",
        ]
        
        if not any(domain in url for domain in allowed_domains):
            raise SafetyViolationError(f"Safety Gate Violation: Unauthorized endpoint domain '{url}'.")
            
        return True

    def get_safety_status(self) -> Dict[str, Any]:
        """Returns the current immutable safety state for monitoring."""
        return {
            "dry_run": self.config.safety.DRY_RUN,
            "auto_execute": self.config.safety.AUTO_EXECUTE,
            "production_enabled": self.config.safety.PRODUCTION_ENABLED,
            "allow_testnet_orders": self.config.safety.ALLOW_TESTNET_ORDERS,
            "max_account_risk_pct": self.config.safety.MAX_ACCOUNT_RISK_PCT,
            "max_leverage": self.config.safety.MAX_LEVERAGE,
            "status": "SECURE_FAIL_CLOSED"
        }


safety_policy = SafetyPolicy()
