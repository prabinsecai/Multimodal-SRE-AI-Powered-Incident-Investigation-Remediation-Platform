# Deployment Rollback & Regression Mitigation Runbook

## Overview
Deployment rollbacks are high-priority corrective interventions triggered when a software release introduces severe regressions, anomalous error rate surges, latency degradation, or fatal boot loops. Safe rollbacks ensure zero-downtime reversion to the last known good artifact while maintaining schema compatibility.

## Rollback Decision Matrix
- **Trigger Severity**: SEV-1 or SEV-2 incident occurring within 30 minutes of a deployment event.
- **Error Rate Condition**: `http_5xx_rate` > 2% or `latency_ms` > 3x normal baseline.
- **Data Safety Check**: Verify database migrations from the bad release are backward-compatible (non-destructive DDL).

## Standard Rollback Procedure
1. **Approval**: Obtain SRE on-call or automated policy approval.
2. **Execution**:
   - For Kubernetes: `kubectl rollout undo deployment/<service-name>` or patch image tag to prior stable version (e.g. `v1.8.2`).
   - For Simulated Platform: Invoke platform API `remediation/{action_id}/approve` with action `rollback_deployment`.
3. **Traffic Shift Verification**: Monitor canary or blue/green weights shifting 100% back to stable version.

## Verification & Post-Rollback Auditing
- Verify active version matches expected stable release tag.
- Monitor error rates, latencies, and pod restart counts for 10 minutes.
- Log audit event with user ID, execution timestamp, and rollback metadata.