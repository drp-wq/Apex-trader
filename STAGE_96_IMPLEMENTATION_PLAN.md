# APEX TRADER — STAGE 96 IMPLEMENTATION PLAN

## Overview

Transform APEX TRADER from a signal-generation system into a **production-grade, safety-first autonomous crypto futures trading platform**.

**Governing Principle:**
> APEX TRADER must prefer NO TRADE over an unsafe or unverifiable trade.

---

## Phase Breakdown

### Phase A: Repository Audit + Baseline Lock ✓ COMPLETE

**Objective:** Verify baseline, establish architecture inventory, implement market data validation.

**Deliverables:**
- ✓ Baseline locked: `554b4c592c7e382a74bf4eac72aaa92fcb68ff6b`
- ✓ Architecture audit complete
- ✓ Market data validation layer (OHLCV, order book, OI, volume, order flow)
- ✓ 32 comprehensive validation tests
- ✓ Data quality classification system
- ✓ NO fabricated data — all validators reject invalid/missing data

**Success Criteria:**
- Baseline 95 tests continue passing
- New validation tests isolated and deterministic
- No schema changes to existing domain models
- Safety layer untouched

---

### Phase B: Order Book, RVOL, OI, Order Flow Integration

**Objective:** Build real-time data pipeline with reliable market data feed.

**Deliverables:**
- Market data provider abstraction
- WebSocket stream manager
- Order book depth manager
- RVOL/OI realtime calculation
- Order flow aggregation (where available)
- Scanner metrics aggregator
- Binance Futures adapter
- Bybit Perpetuals adapter
- Testnet read-only endpoints

**Test Requirements:**
- Market data stream validation
- Reconnection resilience
- Stale data cutoff
- Invalid data rejection
- Metrics calculation determinism
- No data loss under concurrent events

**Acceptance:**
- 15+ scanner markets scanned every 15 seconds
- Market data < 1 second stale
- Order book < 500ms update latency
- All metrics validated before use

---

### Phase C: Market Structure, Regime, Confluence Hardening

**Objective:** Harden existing SMC analysis with deterministic market regime and improved confluence.

**Deliverables:**
- Market regime classifier (TREND_UP, TREND_DOWN, RANGE, HIGH_VOL, LOW_VOL, TRANSITION, UNKNOWN)
- Liquidity detection (equal highs/lows, sweep events, stop-run)
- Volume profile exactness classifier
- Enhanced confluence scoring with data quality weights
- Setup quality gates
- Setup invalidation tracking

**Test Requirements:**
- Regime classification on historical data
- No lookahead bias in structure detection
- Confluence scoring reproducibility
- Data quality impact on confidence

**Acceptance:**
- Confluence scores explainable (reason breakdown)
- Setup validation deterministic
- No signal repainting on replayed data

---

### Phase D: Risk Engine Hardening

**Objective:** Strengthen existing risk controls; add drawdown kill switch, correlation limits.

**Deliverables:**
- Daily drawdown kill switch (NORMAL → WARNING → KILL_SWITCH)
- Correlation group enforcement (BTC_MAJORS, LAYER1S, MEME)
- Position sizing determinism
- Exposure tracking (notional, leverage, margin)
- Account risk limits per profile
- Risk event persistence

**Test Requirements:**
- Kill switch activation and recovery
- Correlation blocking
- Position sizing against constraints
- Margin calculation correctness
- Drawdown calculation

**Acceptance:**
- Kill switch blocks new trades when triggered
- Existing positions protected
- No trades exceed leverage limits
- Correlation violations prevented

---

### Phase E: Decision Brain + Setup Quality

**Objective:** Implement AI reasoning layer on top of deterministic foundation.

**Deliverables:**
- Setup ranker (by quality, confluence, risk-reward)
- Setup explainability (why chosen, why rejected)
- AI fallback policy (deterministic engine if AI unavailable)
- Human-readable reasoning
- Setup acceptance/cancellation workflow
- Auto-execute timeout (configurable)

**Test Requirements:**
- AI output validation
- Fallback behavior on AI unavailability
- Reasoning consistency
- Timeout handling

**Acceptance:**
- AI cannot bypass safety gates
- AI cannot bypass kill switch
- AI cannot change risk limits
- Deterministic engine works if AI fails

---

### Phase F: Execution Safety + Position Management

**Objective:** Hardened execution path with multiple safety gates.

**Deliverables:**
- Execution gate sequence (setup → risk → exposure → drawdown → data freshness → protective verification → execution mode → submit)
- Protective order barrier (SL/TP validation)
- Position state machine (OPEN → PARTIAL_TP → BREAKEVEN → TRAILING → CLOSED/ERROR)
- Emergency flatten (idempotent, fast, auditable)
- Duplicate execution prevention
- Position manager (TP1/TP2/TP3, trailing, breakeven)

**Test Requirements:**
- All gates tested individually and in sequence
- Protective order verification
- Position state transitions
- Emergency flatten idempotence
- No duplicate orders

**Acceptance:**
- No order placed without passing all gates
- Emergency flatten works reliably
- Position states consistent
- Audit trail complete

---

### Phase G: API + WebSocket + Control Center

**Objective:** Expose system through safe, validated APIs.

**Deliverables:**
- /health, /status, /scanner, /setups, /positions, /trades, /risk, /exposure, /config endpoints
- /emergency-flatten POST
- /execution-mode GET/POST
- WebSocket streams (market data, scanner, setups, positions, alerts)
- Control center UI (status, scanner, setups, positions, risk, flatten, mode)
- No credential exposure
- Rate limiting where appropriate

**Test Requirements:**
- API validation
- WebSocket reconnection
- Stale subscription handling
- No secret leakage
- Error message safety

**Acceptance:**
- All endpoints tested
- No credentials in responses
- WebSocket stable under reconnect
- UI reflects actual system state

---

### Phase H: Observability, Security, Deployment

**Objective:** Production readiness.

**Deliverables:**
- Structured logging (timestamp, event_type, symbol, correlation_id, mode, result, reason)
- Health checks (database, market data, exchange, scanner, execution, WebSocket, Telegram)
- Metrics collection (orders placed, fills, errors, latency)
- Audit logging (every trade decision recorded)
- Telegram alerts (setup, fill, SL/TP, risk events)
- Docker / docker-compose
- .env.example with all required configuration
- Persistent database volume
- Health check endpoint for load balancers

**Test Requirements:**
- Logging consistency
- Alert delivery
- Persistence correctness
- Docker build/run

**Acceptance:**
- All events logged and queryable
- Telegram alerts working
- Docker deploy reproducible
- Health checks respond correctly

---

### Phase I: Regression + Production Hardening

**Objective:** Final validation before go-live.

**Deliverables:**
- Full regression test suite
- Stress testing (high-volume markets, rapid price moves)
- Long-running stability test (24h+)
- Testnet end-to-end
- Failover scenarios
- Recovery procedures
- Documentation (architecture, API, deployment, troubleshooting)

**Test Requirements:**
- 100%+ of Stage 96 requirements covered by tests
- No flaky tests
- Deterministic outcomes from historical data
- Graceful degradation under network failures

**Acceptance:**
- All 95 original tests passing
- All new Stage 96 tests passing
- No unattributable warnings
- Performance meets requirements
- Recovery from failures verified

---

### Phase J: Production Readiness Audit

**Objective:** Final sign-off.

**Checklist:**
- ✓ Functional: all subsystems working
- ✓ Safe: paper default, live opt-in, risk limits enforced
- ✓ Tested: comprehensive test coverage
- ✓ Auditable: decision provenance recorded
- ✓ Monitorable: health checks, alerts, logs
- ✓ Documented: architecture, API, deployment
- ✓ Reproducible: Docker, configuration examples
- ✓ Backward compatible: existing API semantics preserved

---

## Key Principles

### 1. FAIL CLOSED
When anything uncertain happens:
- Exchange disconnected → block new trades
- Market data stale → block new trades
- Risk calculation invalid → block trade
- Protective order unavailable → block trade
- Database unavailable → block live execution
- AI unavailable → deterministic fallback
- Unknown execution state → reconcile before proceeding

### 2. NO FABRICATED DATA
- Never invent bid/ask data if unavailable → mark DATA_UNAVAILABLE
- Never silently convert invalid data → reject explicitly
- Missing data reduces confidence, not increases it
- Volume profile approximations marked explicitly

### 3. DETERMINISM
- Same market data → same signal
- No lookahead bias in historical backtesting
- Signal reproducible from historical replay
- Risk calculations audit-able

### 4. SAFETY-FIRST
- Paper/DRY-RUN always default
- Live trading requires explicit configuration
- Risk limits cannot be bypassed
- Kill switch automatic on drawdown threshold
- Every order passes multiple gates
- Protective order verification mandatory

### 5. AUDITABILITY
For every trade candidate, answer:
- Why did scanner select this symbol?
- Why is direction LONG/SHORT?
- Why was setup valid?
- Which SMC structures detected?
- What was confluence score?
- What was risk?
- Why position size chosen?
- Which safety gates passed?
- Why execution allowed/blocked?
- What happened afterward?

---

## Testing Strategy

### Unit Tests
- Individual validator, calculator, gate logic
- Deterministic fixtures
- No real exchange calls
- No real credentials
- Fast execution

### Integration Tests
- Multiple components together
- Realistic data flows
- Marked with `@pytest.mark.integration`
- May be slower

### Regression Tests
- Historical data replay
- Signal reproducibility
- No lookahead verification
- Performance benchmarks

### E2E Tests
- Full pipeline from market data → position
- Paper execution only
- Testnet execution (if needed)
- Live execution blocked by safety gates

---

## Code Quality Standards

### Type Hints
- All function signatures typed
- Return types explicit
- Use `Optional`, `Union`, `Dict`, `List` from typing

### Dataclasses
- Domain models use `@dataclass`
- Enums for fixed values
- Validation in `__post_init__` where appropriate

### Error Handling
- Explicit exception types
- Never silent swallowing
- Clear error messages
- Log level appropriate to severity

### Documentation
- Docstrings on all classes and public methods
- Architecture diagrams in markdown
- API documentation with examples
- Deployment guide

### No Hidden Global State
- Dependency injection for validators, engines
- Configuration object passed in
- Stateful components explicitly tracked
- Thread-safe where needed

---

## Acceptance Criteria

**Stage 96 is complete only when:**

### Functional
- Market data pipeline works
- Scanner works
- SMC analysis works (FVG, OB, liquidity, structure)
- Confluence engine works
- Setup engine works
- Risk engine works
- Execution gates work
- Position management works
- Emergency flatten works
- Database persistence works
- API endpoints work
- WebSocket streams work
- Alerts work

### Safety
- Paper is default execution mode
- Live trading requires explicit opt-in
- Risk limits cannot be bypassed
- Kill switch blocks new trades
- Protective order verification blocks unsafe trades
- Stale data blocks execution
- Missing data does not become fabricated data
- AI cannot bypass deterministic safety
- Duplicate execution prevented
- Emergency flatten is idempotent

### Testing
- Original 95 tests continue passing
- Stage 96 adds meaningful regression tests
- Target: 100%+ of relevant automated tests passing
- No newly introduced warnings/errors

### Quality
- `pytest -q` passes
- `git diff --check` passes
- Type hints on all functions
- Docstrings on all classes
- No circular imports
- Clear separation of concerns

---

## Timeline Estimate

**Assuming continuous work:**

- Phase A: 4-6 hours (DONE)
- Phase B: 8-10 hours
- Phase C: 6-8 hours
- Phase D: 6-8 hours
- Phase E: 4-6 hours
- Phase F: 8-10 hours
- Phase G: 8-10 hours
- Phase H: 4-6 hours
- Phase I: 6-8 hours
- Phase J: 2-4 hours

**Total: 56-76 hours**

---

## Success Metrics

1. **Test Coverage:** 100% of Stage 96 requirements automated
2. **Performance:** Scanner scans 15+ markets every 15 seconds
3. **Safety:** Zero unintended live trades
4. **Reliability:** 99.9%+ uptime in paper mode
5. **Auditability:** Every trade decision fully traceable
6. **Maintainability:** Clear code structure, comprehensive docs

---

## Risk Mitigation

**Risk: Baseline breaks during implementation**
→ Recovery: `git diff` against 554b4c5, revert experimental changes, keep baseline

**Risk: Existing tests fail due to schema changes**
→ Mitigation: Use compatibility layers, preserve external API

**Risk: Performance degradation with validation**
→ Mitigation: Profile early, optimize hot paths, use async I/O

**Risk: Production incident after go-live**
→ Recovery: Emergency flatten, automated risk cutoff, manual shutdown capability

---

**Remember:**
> Correctness, determinism, auditability, risk control, and failure-closed behavior take priority over feature count.
