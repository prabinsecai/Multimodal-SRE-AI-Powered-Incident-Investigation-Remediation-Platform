# Service Dependency Failure Runbook

## Overview
Microservice architectures often suffer from cascading failures when an unisolated downstream dependency (auth service, payment provider, notification worker) degrades, causing upstream request thread pools to queue and crash.

## Key Symptoms & Multimodal Evidence
- **Logs**:
  - `ClientException: Call to downstream auth-api failed with HTTP 503`
  - `CircuitBreaker 'payment-gateway' OPEN; rejecting calls`
- **Metrics**:
  - `dependency_latency_seconds{target="payment-gateway"}` > 2000ms
  - `dependency_error_rate{target="payment-gateway"}` > 25%
- **Traces**:
  - Outbound HTTP / gRPC client spans exceeding timeouts.

## Remediation Strategy
1. **Immediate Mitigation**:
   - Trip circuit breaker manually to return cached or degraded fallback responses.
   - Route traffic to secondary region or backup provider endpoint.
2. **Permanent Resolution**:
   - Introduce bulkhead pattern and dedicated client thread pools per remote service.
   - Enforce bounded timeouts and exponential jittered retries on all RPC clients.

## Verification & Recovery Criteria
- Upstream service error rate returns to normal baseline.
- Dependency circuit breaker transitions from OPEN to HALF-OPEN then CLOSED.
