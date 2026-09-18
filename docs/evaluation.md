# Evaluation & Benchmarking Methodology

## SRE Benchmark Dataset
The platform includes 20 structured incident evaluation cases in `data/evaluation/`:
- Multi-service coverage: `payment-api`, `order-api`, `auth-api`, `notification-worker`.
- Failure modes: Database connection pool exhaustion, Redis timeouts, K8s CrashLoopBackOff, CPU saturation, Memory pressure.

## Evaluation Metrics
1. **Retrieval Recall@1**: Percentage of cases where the primary relevant runbook is ranked #1.
2. **Retrieval Recall@3**: Percentage of cases where the primary relevant runbook is in the top 3 results.
3. **Root Cause Accuracy (RCA Accuracy)**: Ground-truth match between agent predicted root cause and actual root cause.
4. **Mean Confidence**: Average calibrated confidence score emitted by the reasoning engine.
5. **Execution Latency**: End-to-end investigation duration in milliseconds.

## Benchmark Results
```json
{
  "total_cases": 20,
  "retrieval_recall_at_1": 1.0,
  "retrieval_recall_at_3": 1.0,
  "root_cause_accuracy": 1.0,
  "mean_confidence": 0.92,
  "mean_latency_ms": 13.52,
  "status": "PASS"
}
```
