# Kubernetes CrashLoopBackOff & OOMKilled Runbook

## Overview
Kubernetes `CrashLoopBackOff` status indicates that container processes within a pod repeatedly terminate immediately after startup or crash during initial readiness/liveness probe checks. Common triggers include missing required environment variables, failing initial database migrations, application runtime uncaught exceptions, and container memory exceeding cgroup memory limits (`OOMKilled`, exit code 137).

## Key Symptoms & Multimodal Evidence
- **Logs**:
  - `Container terminated with exit code 137 (OOMKilled)`
  - `Application startup failed: missing mandatory environment variable DB_PASSWORD`
  - `Liveness probe failed: HTTP probe failed with statuscode: 503`
  - `Back-off restarting failed container`
- **Metrics**:
  - `container_memory_working_set_bytes` hitting `container_spec_memory_limit_bytes`
  - `k8s_pod_restart_count` incrementing continuously
  - `pod_ready_status` = 0
  - Service replica count available dropping below required minimum
- **Deployments**:
  - Almost always preceded within 1-10 minutes by a new deployment or configmap change.

## Root Cause Analysis
1. **OOMKilled (Exit Code 137)**: Container memory limits set too low for startup heap allocation or JVM warmup.
2. **Missing Config/Secrets**: Container unable to authenticate to dependent database or Vault service on boot.
3. **Failing Health Probes**: Initial delay seconds too short; application killed by kubelet before it finishes initializing.
4. **Fatal Startup Exception**: Incompatible library version or syntax error in newly deployed image tag.

## Remediation Strategy
1. **Immediate Mitigation**:
   - **Rollback Deployment**: `kubectl rollout undo deployment/<service-name>` or trigger platform automated rollback to previous stable replica set.
   - Adjust resource limits temporarily if OOMKilled: Increase `limits.memory` in deployment manifest.
   - Update missing configuration keys in Kubernetes Secret or ConfigMap.
2. **Permanent Resolution**:
   - Tune application memory footprints and JVM `-Xmx` settings.
   - Adjust `initialDelaySeconds` and `periodSeconds` for liveness and readiness probes.

## Verification & Recovery Criteria
- Pod status transitions to `Running` with `Ready: 1/1`.
- Restart count remains static (no new crashes over 10 minutes).
- All endpoints respond with 200 OK to liveness and readiness probe requests.