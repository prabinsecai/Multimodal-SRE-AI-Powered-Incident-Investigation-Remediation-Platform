# Payment API High Latency Runbook

## Overview
Diagnostic runbook for high response latency on `payment-api`. Payment processing transactions must complete within a P99 SLA of 350ms. Latencies exceeding 1000ms indicate unindexed queries, downstream PSP timeouts, or thread pool starvation.

## Investigation Steps
1. Examine trace spans to differentiate SQL latency from outbound Stripe/PSP gateway latency.
2. Check CPU and memory utilization on payment-api pods.
3. Review database lock wait times and active connection counts.

## Remediation Steps
1. Scale up payment-api replicas if CPU saturation is detected.
2. Rollback recent release if latency spike correlates with deployment event.
3. Enable query cache or temporary rate limiting on high-frequency clients.