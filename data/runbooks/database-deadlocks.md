# Database Deadlocks & Transaction Lock Contention Runbook

## Overview
Database deadlocks occur when two or more concurrent transactions hold locks on different table rows or resources and each attempts to acquire a lock held by the other, forming a cyclic dependency. The database engine automatically detects the cycle and aborts one of the transactions with a deadlock error (`40P01` in PostgreSQL).

## Key Symptoms & Multimodal Evidence
- **Logs**:
  - `ERROR: deadlock detected`
  - `Detail: Process 12345 waits for ExclusiveLock on tuple; blocked by process 67890.`
  - `TransactionRollbackError: deadlock detected`
- **Metrics**:
  - `db_deadlocks_total` incrementing rapidly
  - `db_lock_wait_time_ms` spiking on specific table relations
  - `transaction_rollback_rate` > 2%
- **Traces**:
  - Database spans failing with error status after multiple retries.

## Root Cause Analysis
1. **Inconsistent Lock Acquisition Order**: Multiple application threads updating related rows in opposite order (e.g. Account A then Account B vs Account B then Account A).
2. **Long-Running Bulk Transactions**: Batch jobs locking large table partitions while online OLTP transactions attempt updates on single rows.
3. **Missing Foreign Key Indexes**: Updates cascading table-level or range locks due to unindexed foreign keys.

## Remediation Strategy
1. **Immediate Mitigation**:
   - Throttle concurrent batch operations running in parallel with OLTP traffic.
   - Configure transaction retry logic with exponential backoff in application services.
2. **Permanent Resolution**:
   - Enforce deterministic alphabetical or primary key lock ordering across all transactional write paths.
   - Add missing indexes on foreign key columns.
   - Keep transactions concise, acquiring locks as late as possible.

## Verification & Recovery Criteria
- Zero deadlock exceptions in database logs over 15 minutes.
- Transaction rollback rate returns to < 0.01%.
