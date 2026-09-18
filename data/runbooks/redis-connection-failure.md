# Redis Latency & Connection Failure Runbook

## Overview
Redis connection failures or high command latency occur when the in-memory cache/broker experiences CPU saturation, blocking commands (e.g. `KEYS *`, large `HGETALL`), maxmemory eviction pressure, or network partition between application worker nodes and the Redis cluster.

## Key Symptoms & Multimodal Evidence
- **Logs**:
  - `redis.exceptions.ConnectionError: Error while reading from socket`
  - `OOM command not allowed when used memory > 'maxmemory'`
  - `Timeout connecting to redis host:6379 after 2000ms`
  - `redis.exceptions.BusyLoadingError`
- **Metrics**:
  - `redis_command_latency_ms` > 50ms (baseline < 2ms)
  - `redis_connected_clients` spiking to maximum limit
  - `redis_memory_used_ratio` > 95%
  - `cache_miss_rate` increasing rapidly, causing cache stampede to SQL database
- **Traces**:
  - Cache lookup spans (`redis.get`, `redis.set`) timing out or returning error status
  - Cascading database load increase in downstream traces

## Root Cause Analysis
1. **Expensive Slow Commands**: Developers or automated scripts issuing $O(N)$ operations (`KEYS *`, `SMEMBERS` on giant sets) blocking single-threaded Redis event loop.
2. **Connection Pool Exhaustion**: Client applications opening new Redis sockets per request rather than maintaining a shared connection pool.
3. **Memory Saturation**: Redis reaching `maxmemory` without appropriate eviction policy (`volatile-lru` or `allkeys-lru`), leading to write rejections.

## Remediation Strategy
1. **Immediate Mitigation**:
   - Check `SLOWLOG GET 10` and kill/block expensive long-running commands.
   - Flush non-essential cache partitions (`redis-cli flushdb async`) if temporary memory relief is critical.
   - Scale Redis replica reading or restart stalled Redis instance.
   - Fall back to degraded cache-bypass mode in application settings.
2. **Permanent Resolution**:
   - Replace `KEYS` with `SCAN` in application code.
   - Implement client-side connection pooling and circuit breaking with Sentinel/Cluster failover.

## Verification & Recovery Criteria
- `redis_command_latency_ms` drops below 3ms.
- Application error rates for cache operations return to 0%.
- Client connection counts stabilize within configured pool limits.