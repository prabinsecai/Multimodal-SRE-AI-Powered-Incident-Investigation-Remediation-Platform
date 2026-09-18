# CPU Saturation & Thread Pool Starvation Runbook

## Overview
CPU saturation occurs when total CPU utilization across worker instances or nodes reaches 100%, causing the Linux scheduler to throttle container CFS quotas and starve application runtime threads. This induces severe response time spikes, queue backlog growth, and eventual request timeouts.

## Key Symptoms & Multimodal Evidence
- **Logs**:
  - `Thread pool exhausted; rejected execution of task`
  - `Worker thread starvation detected: task delayed by 4500ms`
  - `Slow event loop heartbeat: block duration 320ms`
- **Metrics**:
  - `cpu_utilization` > 90% (sustained across multiple pods)
  - `container_cpu_cfs_throttled_seconds_total` spiking rapidly
  - `request_queue_depth` expanding beyond normal baseline
  - `p99_latency_ms` increasing from 50ms to > 3000ms
- **Traces**:
  - Broad latency increases across all HTTP spans without a single localized database or network bottleneck.

## Root Cause Analysis
1. **Unoptimized CPU Intensive Loops**: Inefficient serialization/deserialization routines or cryptographic operations introduced in recent patch.
2. **Denial of Service / Traffic Surge**: Influx of complex search or report generation requests.
3. **CFS Throttling**: Strict Kubernetes CPU limits set too low relative to multi-threaded runtime requirements.

## Remediation Strategy
1. **Immediate Mitigation**:
   - **Horizontal Autoscaling (HPA)**: Scale out replica count (`kubectl scale deployment <service> --replicas=N`).
   - Rate limit incoming non-critical traffic at API gateway.
   - Roll back if regression followed a deployment.
2. **Permanent Resolution**:
   - Profile CPU hotspots with async-profiler or py-spy.
   - Remove CPU limits or adjust CPU quotas to avoid CFS throttling spikes.

## Verification & Recovery Criteria
- Average pod `cpu_utilization` stabilizes between 40% and 65%.
- `container_cpu_cfs_throttled_seconds_total` flattens to zero.
- Latency percentiles return to normal baseline.
