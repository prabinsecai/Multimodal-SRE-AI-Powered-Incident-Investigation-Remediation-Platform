# PostgreSQL Connection Pool Exhaustion Runbook

## Overview
PostgreSQL connection pool exhaustion occurs when the application service exhausts available active and idle connections in its client pool (e.g. HikariCP, asyncpg, PgBouncer) or reaches the database server's `max_connections` ceiling. This leads to connection acquisition timeouts, cascading query backpressure, and elevated HTTP 500 / 504 Gateway Timeout responses.

## Key Symptoms & Multimodal Evidence
- **Logs**:
  - `database timeout acquiring connection from pool`
  - `remaining connection slots are reserved for non-replication superuser connections`
  - `sorry, too many clients already`
  - `asyncpg.exceptions.TooManyConnectionsError`
  - `Connection pool exhausted; queue timeout exceeded (30000ms)`
- **Metrics**:
  - `db_connection_utilization` > 90%
  - `db_pool_active_connections` reaches capacity limit (e.g., 50/50)
  - `db_pool_wait_duration_ms` spikes significantly (> 1000ms)
  - `http_5xx_rate` spikes > 5-15%
  - `latency_ms` (P95/P99) increases from ~80ms to > 1500ms
- **Traces**:
  - Spans named `db.acquire_connection` or `db.query` taking > 1.0s or returning `ERROR` status
  - Cascading latency on downstream HTTP entry points
- **Deployments**:
  - Frequently correlated with recent deployments that introduced unindexed N+1 queries, unclosed connection leaks, or misconfigured pool size parameters.

## Root Cause Analysis
1. **Connection Leak**: Application threads acquire database connections without releasing them in `finally` blocks or deferring release until request termination.
2. **Slow Query Saturation**: A long-running unindexed query locks worker connections, causing new requests to queue up until the pool is exhausted.
3. **Traffic Spike vs Pool Size**: Sudden request rate increase without dynamic pool autoscaling or read replica offloading.
4. **Recent Code Regression**: Deployment introducing higher concurrency demands or transaction hold durations.

## Remediation Strategy
1. **Immediate Mitigation (Low/Medium Risk)**:
   - Restart service pods / instances gracefully to flush leaked connection handles.
   - If a recent release is identified, trigger **Deployment Rollback** to the prior known stable version (`rollback_deployment`).
   - Scale connection pool capacity on PgBouncer / proxy layer if database server headroom permits.
2. **Permanent Resolution**:
   - Add database indexing for slow queries holding transactions open.
   - Ensure all connection handles use scoped context managers (`async with pool.acquire():`).
   - Configure statement timeouts (`statement_timeout = 5000`) and idle connection timeouts.

## Verification & Recovery Criteria
- `db_connection_utilization` drops below 60%.
- `http_5xx_rate` returns to baseline (< 0.1%).
- `latency_ms` P99 returns to < 200ms.
- Zero `database timeout` error logs over a 5-minute rolling window.