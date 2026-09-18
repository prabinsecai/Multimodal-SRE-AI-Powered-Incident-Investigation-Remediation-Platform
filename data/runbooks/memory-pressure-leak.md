# Memory Pressure & Memory Leak Runbook

## Overview
Memory leaks occur when application memory (heap, native allocations, or global caches) grows monotonically over time without being reclaimed by garbage collection. As memory usage approaches container limits, the operating system kernel triggers the Out-Of-Memory killer (`OOMKilled`, exit code 137), terminating worker processes abruptly.

## Key Symptoms & Multimodal Evidence
- **Logs**:
  - `java.lang.OutOfMemoryError: Java heap space`
  - `MemoryError: Unable to allocate array`
  - `Node.js JavaScript heap out of memory`
  - `Process killed by OOM killer`
- **Metrics**:
  - `container_memory_working_set_bytes` exhibiting continuous saw-tooth upward trend without returning to baseline after garbage collection
  - `gc_pause_duration_seconds` increasing dramatically as full GCs fail to reclaim memory
  - `http_5xx_rate` spiking intermittently as crashed workers fail in-flight requests
- **Traces**:
  - Prematurely terminated spans (`status=ERROR`, `error=connection reset by peer`)

## Root Cause Analysis
1. **Unbounded In-Memory Caches**: Dictionaries, LRU caches without maximum size limits, or unevicted event listener registrations.
2. **Unclosed Resource Buffers**: File handles, byte buffers, or streaming payloads read entirely into memory.
3. **Session State Retention**: Storing unbounded user session objects in local memory rather than distributed stores.

## Remediation Strategy
1. **Immediate Mitigation**:
   - Perform rolling restart of service instances to reset memory footprints.
   - Temporarily increase container memory limits in Helm/Kubernetes values.
   - Roll back to the preceding release if memory growth began post-deployment.
2. **Permanent Resolution**:
   - Analyze heap dumps (e.g. `jmap`, `heapdump.heapsnapshot`, `tracemalloc`).
   - Bound all caching structures with TTL and size eviction policies.

## Verification & Recovery Criteria
- Memory utilization stabilizes at < 70% of limit with healthy GC reclamation cycles.
- Pod uptime remains continuous without OOM terminations.
- Error rates return to zero.
