# Payment API Database Timeout Runbook

## Overview
Specific runbook for Payment API (`payment-api`) database timeout incidents. Occurs when connection pool saturation or heavy transaction volume prevents checkout requests from obtaining SQL query locks or connection slots within the 30-second SLA limit.

## Diagnostic Checklist
1. Review recent deployments for `payment-api` (e.g. `v1.8.3`).
2. Inspect connection pool utilization metrics: `db_connection_utilization`, `http_5xx_rate`.
3. Check error log patterns: `database timeout acquiring connection from pool`.
4. Correlate with historical incidents `eval-01` through `eval-20`.

## Remediation Procedure
1. If deployment `v1.8.3` was deployed within the last 30 minutes, execute immediate rollback to `v1.8.2` via `remediation_action: rollback_deployment`.
2. Flush leaked connections and restart pool workers.
3. Validate recovery using post-remediation health check.