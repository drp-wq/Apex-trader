# TEST_REPORT.md — APEX TRADER

## 1. Test Discovery & Execution Summary

- **Total Test Files:** 16
- **Test Runner:** `pytest` / `unittest`
- **Result:** 95 PASSED, 0 FAILED, 0 SKIPPED

---

## 2. Comprehensive Test Breakdown

| Category | Test File | Tests | Status |
| :--- | :--- | :--- | :--- |
| **Foundations & Domain** | `tests/test_stage1_foundation.py` | 5 | PASSED |
| **Domain Semantics** | `tests/test_semantics.py` | 4 | PASSED |
| **Risk / Reward Math** | `tests/test_rr.py` | 5 | PASSED |
| **Open Interest Math** | `tests/test_oi.py` | 4 | PASSED |
| **Safety & Barriers** | `tests/test_safety_gates.py` | 8 | PASSED |
| **Market Data Providers** | `tests/test_market_data_provider.py` | 4 | PASSED |
| **WebSocket Streamer** | `tests/test_market_data_ws.py` | 5 | PASSED |
| **Scanner & Metrics** | `tests/test_scanner_metrics.py` | 5 | PASSED |
| **Market Structure (SMC)** | `tests/test_analysis_market_structure.py` | 3 | PASSED |
| **Fair Value Gaps (FVG)** | `tests/test_analysis_fvg.py` | 2 | PASSED |
| **Order Blocks (OB)** | `tests/test_analysis_order_blocks.py` | 2 | PASSED |
| **Liquidity Sweeps** | `tests/test_analysis_liquidity.py` | 2 | PASSED |
| **Volume Profile** | `tests/test_analysis_volume_profile.py` | 2 | PASSED |
| **Confluence Engine** | `tests/test_analysis_confluence.py` | 5 | PASSED |
| **Trade Setup Engine** | `tests/test_analysis_setup_engine.py` | 4 | PASSED |
| **Deterministic Risk Engine**| `tests/test_risk_deterministic_engine.py` | 5 | PASSED |
| **Risk Integration** | `tests/test_risk_integration.py` | 4 | PASSED |
| **Paper Trading Simulator**| `tests/test_paper_engine.py` | 4 | PASSED |
| **Protective Orders Barrier**| `tests/test_protective_orders.py` | 6 | PASSED |
| **Emergency Flatten** | `tests/test_emergency_flatten.py` | 2 | PASSED |
| **Historical Replay** | `tests/test_replay_engine.py` | 2 | PASSED |
| **Binance Testnet Read** | `tests/test_binance_testnet.py` | 3 | PASSED |
| **FastAPI Endpoints** | `tests/test_api_endpoints.py` | 4 | PASSED |
| **SQLite Persistence** | `tests/test_database.py` | 1 | PASSED |
| **Telegram Notifications** | `tests/test_telegram_alerts.py` | 3 | PASSED |
| **Full System E2E Pipeline**| `tests/test_full_system_e2e.py` | 1 | PASSED |

**Total Tests Executed:** 95
