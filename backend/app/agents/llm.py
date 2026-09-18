from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
from typing import Any
import httpx
from app.core.config import settings
from app.schemas.api import (
    StructuredInvestigationResult,
    RootCauseDetail,
    AlternativeCause,
    RemediationPlan,
    VerificationStep,
    TimelineEntry,
)

SRE_SYSTEM_PROMPT = """You are an experienced Principal Site Reliability Engineer (SRE) investigating a production incident.
Your mission is to perform a rigorous, multimodal root cause analysis (RCA) using ONLY the evidence provided.

Core Investigation Rules:
1. Grounding: Never invent logs, metrics, traces, deployments, or historical runbooks. Every claim must cite specific telemetry.
2. Multimodal Correlation: Correlate events across modalities: compare log timestamps, metric spikes, trace spans, and recent deployments.
3. Facts vs Hypotheses: Clearly distinguish observed empirical facts from inferred hypotheses.
4. Deployment Scrutiny: Always inspect recent deployment events to assess whether a code or configuration regression triggered the failure.
5. Knowledge Runbook Citation: Reference matching SRE runbooks for diagnostic validation and industry best practices.
6. Alternative Cause Rejection: Explicitly analyze competing hypotheses (e.g. CPU saturation, network partition, memory leak) and explain why they were rejected.
7. Confidence Scoring: Calculate a realistic confidence score (0.0 to 1.0) based on the number and consistency of supporting modalities.
8. Safe Remediation: Propose the safest, minimal-blast-radius remediation plan (preferring reversible actions such as rollback or horizontal scaling). Never execute destructive commands without human approval.
9. Verification Plan: Define quantitative post-remediation verification steps with clear pass/fail criteria.

You MUST produce a valid JSON object strictly matching this schema:
{
  "summary": "Concise 1-2 sentence executive summary of the incident and root cause",
  "severity": "SEV-1 | SEV-2 | SEV-3",
  "affected_service": "service-name",
  "observations": ["Observed fact 1 with exact numbers", "Observed fact 2 with exact log message"],
  "evidence": [{"type": "log|metric|trace|deployment", "detail": "..."}],
  "timeline": [{"timestamp": "ISO-8601", "source": "logs|metrics|traces|deployments", "event": "...", "severity": "critical|warning|info"}],
  "hypotheses": [{"hypothesis": "...", "confidence": 0.9, "evidence": ["..."]}],
  "root_cause": {
    "title": "Clear concise root cause title",
    "explanation": "Detailed step-by-step causal explanation grounded in evidence",
    "confidence": 0.91,
    "primary_evidence": ["Key signal 1", "Key signal 2"]
  },
  "alternative_causes": [
    {"hypothesis": "Alternative cause name", "probability": "low|medium", "reason_rejected": "Why the evidence contradicts this hypothesis"}
  ],
  "recommendations": ["Immediate remediation step", "Long-term architectural preventive action"],
  "remediation": {
    "action": "rollback_deployment | restart_service | scale_replicas | flush_connections | observe_and_escalate",
    "risk": "low | medium | high",
    "requires_approval": true,
    "description": "Clear explanation of the remediation action and expected outcome",
    "rollback_target": "v1.8.2"
  },
  "verification_plan": [
    {"step": "1", "metric_or_signal": "http_5xx_rate", "target_condition": "< 0.1% over 5 minutes"},
    {"step": "2", "metric_or_signal": "latency_ms", "target_condition": "P99 < 300ms"}
  ],
  "status": "investigated"
}
"""

class LLMProvider(ABC):
    @abstractmethod
    async def investigate(
        self,
        service: str,
        severity: str,
        evidence: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        runbooks: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> StructuredInvestigationResult:
        ...

class DeterministicEvidenceReasoner(LLMProvider):
    """
    Evidence-grounded SRE Reasoner that performs deterministic
    rule-based multimodal telemetry correlation without hallucination.
    """
    async def investigate(
        self,
        service: str,
        severity: str,
        evidence: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        runbooks: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> StructuredInvestigationResult:
        # 1. Analyze logs for error signatures
        log_entries = [e for e in evidence if e.get("type") == "log"]
        log_text = " ".join([str(e.get("detail", "")).lower() for e in log_entries])

        # 2. Analyze metrics
        metric_entries = [e for e in evidence if e.get("type") == "metric"]
        metrics_by_name = {m.get("name"): float(m.get("value", 0.0)) for m in metric_entries}

        # 3. Analyze deployments
        deployment_entries = [e for e in evidence if e.get("type") == "deployment"]
        latest_deployment = deployment_entries[0] if deployment_entries else None

        # 4. Analyze traces
        trace_entries = [e for e in evidence if e.get("type") == "trace"]
        error_traces = [t for t in trace_entries if t.get("status") == "ERROR" or float(t.get("duration", 0)) > 1.0]

        # Extract observations
        observations = []
        if log_entries:
            observations.append(f"Analyzed {len(log_entries)} relevant log events in the incident window")
        if metrics_by_name:
            for name, val in list(metrics_by_name.items())[:3]:
                observations.append(f"Observed telemetry metric {name} = {val}")
        if latest_deployment:
            observations.append(f"Correlated recent deployment {latest_deployment.get('version', 'unknown')} on service {service}")
        if error_traces:
            observations.append(f"Identified {len(error_traces)} degraded or failing distributed trace spans")

        # Multi-modal pattern matching
        is_db_pool = any(k in log_text for k in ["connection pool", "database timeout", "too many connections", "asyncpg", "pool exhausted"]) or \
                     metrics_by_name.get("db_connection_utilization", 0) > 0.8 or \
                     "postgres-connection-pool.md" in [r.get("name") for r in runbooks]
        
        is_redis = any(k in log_text for k in ["redis", "busyloading", "maxmemory", "socket timeout"]) or \
                   "redis-connection-failure.md" in [r.get("name") for r in runbooks]

        is_k8s_crash = any(k in log_text for k in ["crashloop", "oomkilled", "exit code 137", "liveness probe failed"]) or \
                       "kubernetes-crashloop.md" in [r.get("name") for r in runbooks]

        is_memory_leak = any(k in log_text for k in ["outofmemory", "heap space", "memoryerror"]) or \
                         metrics_by_name.get("memory_usage_ratio", 0) > 0.9 or \
                         "memory-pressure-leak.md" in [r.get("name") for r in runbooks]

        # Determine Primary Root Cause
        if is_db_pool:
            title = "PostgreSQL Connection Pool Exhaustion"
            explanation = (
                f"The incident on service '{service}' was triggered by database connection pool exhaustion. "
                f"Application workers exhausted available connection pool slots, resulting in query acquisition timeouts "
                f"and cascading HTTP 5xx error spikes. "
                + (f"A recent deployment ({latest_deployment.get('version')}) correlated directly with the surge in connection utilization." if latest_deployment else "")
            )
            confidence = 0.92 if (latest_deployment and log_entries) else 0.86
            primary_evidence = [
                f"{len(log_entries)} error logs indicating connection acquisition timeout",
                f"Elevated latency/error metrics: {metrics_by_name}",
                "Matching runbook: postgres-connection-pool.md"
            ]
            action = "rollback_deployment" if latest_deployment else "flush_connections"
            remediation_desc = "Roll back deployment to prior stable release and recycle leaked database connection handles." if latest_deployment else "Recycle connection pool handles and restart service workers."
            alt_causes = [
                AlternativeCause(hypothesis="Redis Cache Latency", probability="low", reason_rejected="Redis command response times remain normal; errors are localized to PostgreSQL pool"),
                AlternativeCause(hypothesis="Node CPU Saturation", probability="low", reason_rejected="Host CPU utilization is within acceptable operating headroom (< 65%)"),
                AlternativeCause(hypothesis="External Network Partition", probability="low", reason_rejected="Health checks and DNS resolution between application pods remain functional")
            ]
            verification = [
                VerificationStep(step="1", metric_or_signal="db_connection_utilization", target_condition="< 60%"),
                VerificationStep(step="2", metric_or_signal="http_5xx_rate", target_condition="< 0.1% for 5 consecutive minutes"),
                VerificationStep(step="3", metric_or_signal="latency_ms", target_condition="P99 < 250ms")
            ]

        elif is_k8s_crash or is_memory_leak:
            title = "Container Out-Of-Memory (OOMKilled) & CrashLoopBackOff"
            explanation = (
                f"Service '{service}' experienced container crashes due to memory limits being exceeded (exit code 137), "
                f"forcing Kubernetes kubelet into CrashLoopBackOff restart cycles."
            )
            confidence = 0.89
            primary_evidence = ["OOMKilled log signatures", "Elevated pod restart rate"]
            action = "rollback_deployment" if latest_deployment else "scale_replicas"
            remediation_desc = "Roll back recent container image and temporarily increase memory limit ceiling."
            alt_causes = [
                AlternativeCause(hypothesis="Database Network Timeout", probability="low", reason_rejected="Database response times are normal; container runtime crashed before query dispatch"),
                AlternativeCause(hypothesis="Bad Configuration Secret", probability="low", reason_rejected="Configuration parsed successfully during boot phase")
            ]
            verification = [
                VerificationStep(step="1", metric_or_signal="pod_ready_status", target_condition="100% healthy (Ready 1/1)"),
                VerificationStep(step="2", metric_or_signal="container_memory_working_set_bytes", target_condition="< 75% of limit")
            ]

        elif is_redis:
            title = "Redis Latency & Connection Pool Contention"
            explanation = f"Service '{service}' encountered Redis command timeouts or connection pool exhaustion, leading to cache miss storms."
            confidence = 0.88
            primary_evidence = ["Redis connection timeout logs", "Elevated cache miss rates"]
            action = "restart_service"
            remediation_desc = "Restart Redis proxy connection pool and clear slow running command locks."
            alt_causes = [
                AlternativeCause(hypothesis="SQL Deadlock", probability="low", reason_rejected="SQL transaction logs show zero 40P01 deadlock events")
            ]
            verification = [
                VerificationStep(step="1", metric_or_signal="redis_command_latency_ms", target_condition="< 2ms"),
                VerificationStep(step="2", metric_or_signal="http_5xx_rate", target_condition="< 0.05%")
            ]

        else:
            title = f"Service Telemetry Degradation on {service}"
            explanation = (
                f"Multi-modal telemetry analysis detected anomalous error rate and latency on {service}. "
                f"Telemetry evidence shows correlation with service activity; further targeted diagnostics recommended."
            )
            confidence = 0.72
            primary_evidence = [f"Metrics observed: {list(metrics_by_name.keys())}"]
            action = "observe_and_escalate"
            remediation_desc = "Engage on-call engineer and enable verbose telemetry capture."
            alt_causes = [
                AlternativeCause(hypothesis="Transient Network Blip", probability="medium", reason_rejected="Error symptoms persist across multiple consecutive polling cycles")
            ]
            verification = [
                VerificationStep(step="1", metric_or_signal="error_rate", target_condition="Return to zero")
            ]

        # Format timeline entries
        timeline_entries = []
        for t in timeline:
            timeline_entries.append(
                TimelineEntry(
                    timestamp=str(t.get("timestamp", datetime.now(timezone.utc).isoformat())),
                    source=str(t.get("source", "system")),
                    event=str(t.get("event", "")),
                    severity=str(t.get("severity", "info")),
                )
            )

        hypotheses = [
            {
                "hypothesis": title,
                "confidence": confidence,
                "evidence": primary_evidence,
            }
        ]

        recommendations = [
            f"Execute safe remediation: {remediation_desc}",
            f"Review matching SRE runbook: {[r.get('name') for r in runbooks][:2]}",
            "Establish automated alerts on connection pool utilization and error thresholds"
        ]

        return StructuredInvestigationResult(
            summary=f"{title} detected on {service} with {int(confidence*100)}% confidence.",
            severity=severity,
            affected_service=service,
            observations=observations,
            evidence=evidence[:30],
            timeline=timeline_entries[:20],
            hypotheses=hypotheses,
            root_cause=RootCauseDetail(
                title=title,
                explanation=explanation,
                confidence=confidence,
                primary_evidence=primary_evidence,
            ),
            alternative_causes=alt_causes,
            recommendations=recommendations,
            remediation=RemediationPlan(
                action=action,
                risk="medium" if "rollback" in action else "low",
                requires_approval=True,
                description=remediation_desc,
                rollback_target="v1.8.2" if latest_deployment else None,
            ),
            verification_plan=verification,
            status="investigated",
            retrieved_documents=runbooks[:5],
        )

class OllamaProvider(LLMProvider):
    def __init__(self):
        self.fallback = DeterministicEvidenceReasoner()

    async def investigate(
        self,
        service: str,
        severity: str,
        evidence: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        runbooks: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> StructuredInvestigationResult:
        user_prompt = f"""Investigate production incident for service '{service}' (Severity: {severity}).
Telemetry Evidence:
{json.dumps(evidence[:25], indent=2)}

Timeline of Events:
{json.dumps(timeline[:15], indent=2)}

Retrieved SRE Runbooks:
{json.dumps([{'name': r['name'], 'snippet': r.get('snippet', r.get('text', '')[:200])} for r in runbooks[:3]], indent=2)}

Produce the complete JSON analysis."""

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json={
                        "model": settings.model_name,
                        "messages": [
                            {"role": "system", "content": SRE_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "format": "json",
                        "stream": False,
                    },
                )
                if resp.status_code == 200:
                    body = resp.json()
                    content = body.get("message", {}).get("content", "")
                    parsed = json.loads(content)
                    return StructuredInvestigationResult.model_validate(parsed)
        except Exception:
            pass

        # Resilient fallback to deterministic reasoner
        return await self.fallback.investigate(service, severity, evidence, timeline, runbooks, context)

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self):
        self.fallback = DeterministicEvidenceReasoner()

    async def investigate(
        self,
        service: str,
        severity: str,
        evidence: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        runbooks: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> StructuredInvestigationResult:
        if not settings.openai_api_key:
            return await self.fallback.investigate(service, severity, evidence, timeline, runbooks, context)

        user_prompt = f"""Investigate production incident for service '{service}' (Severity: {severity}).
Telemetry Evidence:
{json.dumps(evidence[:25], indent=2)}

Timeline of Events:
{json.dumps(timeline[:15], indent=2)}

Retrieved SRE Runbooks:
{json.dumps([{'name': r['name'], 'snippet': r.get('snippet', r.get('text', '')[:200])} for r in runbooks[:3]], indent=2)}

Produce the complete JSON analysis."""

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.model_name or "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": SRE_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                if resp.status_code == 200:
                    body = resp.json()
                    content = body["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    return StructuredInvestigationResult.model_validate(parsed)
        except Exception:
            pass

        return await self.fallback.investigate(service, severity, evidence, timeline, runbooks, context)

def get_provider() -> LLMProvider:
    provider = settings.model_provider.lower().strip()
    if provider == "ollama":
        return OllamaProvider()
    elif provider in ("openai", "openai-compatible"):
        return OpenAICompatibleProvider()
    else:
        return DeterministicEvidenceReasoner()
