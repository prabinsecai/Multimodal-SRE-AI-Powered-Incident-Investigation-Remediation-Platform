# HTTP 5xx Spikes & Gateway Timeout Troubleshooting Runbook

## Overview
HTTP 5xx error spikes (500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout) signal application crashes, upstream service unresponsiveness, or network routing failures between the ingress proxy and backend workers.

## Key Symptoms & Multimodal Evidence
- **Logs**:
  - `HTTP 504: Gateway Timeout to upstream microservice`
  - `HTTP 502: Bad Gateway, connection reset by peer`
  - `Unhandled server exception in request handler`
- **Metrics**:
  - `http_5xx_rate` > 1% (critical severity if > 5%)
  - `http_requests_total{status=~"5.."}` spiking
  - `upstream_response_time_seconds` exceeding gateway timeout limits (e.g. 30s or 60s)
- **Traces**:
  - Ingress span showing HTTP 504 with parent HTTP 500 returned to client, pinpointing upstream dependency that exceeded timeout.

## Root Cause Analysis
1. **Upstream Dependency Slowdown**: Downstream database, Redis cache, or 3rd-party payment gateway unresponsive.
2. **Proxy / Ingress Timeout Mismatch**: Gateway timeout set lower than backend processing timeout.
3. **Application Thread Hang**: Deadlock, infinite loop, or synchronized block contention blocking request handling.

## Remediation Strategy
1. **Immediate Mitigation**:
   - Identify slow upstream via distributed traces and enable circuit breaker or degraded fallback response.
   - If caused by bad release, issue immediate rollback (`rollback_deployment`).
   - Scale backend pods to handle queued requests.
2. **Permanent Resolution**:
   - Configure strict client timeouts on all outbound HTTP/RPC calls with jittered retries.
   - Align gateway and application timeouts properly.

## Verification & Recovery Criteria
- `http_5xx_rate` drops below 0.05%.
- Upstream response times recover within SLA thresholds.
