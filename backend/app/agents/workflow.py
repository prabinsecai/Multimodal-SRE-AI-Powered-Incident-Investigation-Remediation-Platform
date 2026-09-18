from datetime import datetime, timezone
from typing import TypedDict, Any, Callable, Coroutine
from langgraph.graph import StateGraph, END
from sqlalchemy import select
from app.core.db import Session
from app.models.models import Log, Metric, Trace, Incident, Service, DeploymentEvent
from app.rag.hybrid import HybridRetriever, load_runbooks
from app.agents.llm import get_provider
from app.schemas.api import StructuredInvestigationResult

class IncidentState(TypedDict, total=False):
    incident_id: int
    service: str
    severity: str
    title: str
    detected_at: str
    environment: str
    logs: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    traces: list[dict[str, Any]]
    deployments: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    retrieved_documents: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    root_cause: dict[str, Any]
    confidence: float
    alternative_causes: list[dict[str, Any]]
    recommendations: list[str]
    remediation_plan: dict[str, Any]
    verification_plan: list[dict[str, Any]]
    structured_result: dict[str, Any]
    on_step_callback: Any

def build_workflow(step_callback: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]] | None = None):
    retriever = HybridRetriever(load_runbooks())

    async def emit_step(name: str, payload: dict[str, Any]):
        if step_callback:
            try:
                await step_callback(name, payload)
            except Exception:
                pass

    async def context_node(state: IncidentState) -> IncidentState:
        async with Session() as db:
            inc = await db.get(Incident, state['incident_id'])
            svc = await db.get(Service, inc.service_id) if inc else None

            service_name = svc.name if svc else state.get('service', 'unknown')
            severity = inc.severity if inc else state.get('severity', 'SEV-2')
            title = inc.title if inc else 'Incident investigation'
            detected_at = inc.detected_at.isoformat() if inc and inc.detected_at else datetime.now(timezone.utc).isoformat()
            environment = svc.environment if svc else 'production'

        await emit_step("context_loaded", {
            "service": service_name,
            "severity": severity,
            "title": title
        })

        return {
            **state,
            "service": service_name,
            "severity": severity,
            "title": title,
            "detected_at": detected_at,
            "environment": environment,
        }

    async def telemetry_node(state: IncidentState) -> IncidentState:
        service_name = state['service']
        async with Session() as db:
            # Query recent logs
            log_rows = (await db.execute(
                select(Log)
                .where(Log.service == service_name)
                .order_by(Log.timestamp.desc())
                .limit(50)
            )).scalars().all()

            # Query recent metrics
            metric_rows = (await db.execute(
                select(Metric)
                .where(Metric.service == service_name)
                .order_by(Metric.timestamp.desc())
                .limit(100)
            )).scalars().all()

            # Query recent traces
            trace_rows = (await db.execute(
                select(Trace)
                .where(Trace.service == service_name)
                .order_by(Trace.timestamp.desc())
                .limit(50)
            )).scalars().all()

            # Query recent deployments
            deploy_rows = (await db.execute(
                select(DeploymentEvent)
                .where(DeploymentEvent.service == service_name)
                .order_by(DeploymentEvent.timestamp.desc())
                .limit(10)
            )).scalars().all()

        logs_data = [{"service": log.service, "level": log.level, "message": log.message, "timestamp": log.timestamp.isoformat()} for log in log_rows]
        metrics_data = [{"name": m.metric_name, "value": m.value, "timestamp": m.timestamp.isoformat()} for m in metric_rows]
        traces_data = [{"trace_id": t.trace_id, "span_id": t.span_id, "duration": t.duration, "status": t.status, "timestamp": t.timestamp.isoformat()} for t in trace_rows]
        deployments_data = [{"version": d.version, "status": d.status, "timestamp": d.timestamp.isoformat(), "metadata": d.metadata_} for d in deploy_rows]

        evidence: list[dict[str, Any]] = []
        for log in logs_data[:15]:
            evidence.append({"type": "log", "detail": f"[{log['level']}] {log['message']}", "timestamp": log["timestamp"]})
        for m in metrics_data[:20]:
            evidence.append({"type": "metric", "name": m["name"], "value": m["value"], "timestamp": m["timestamp"]})
        for t in traces_data[:10]:
            evidence.append({"type": "trace", "duration": t["duration"], "status": t["status"], "trace_id": t["trace_id"], "timestamp": t["timestamp"]})
        for d in deployments_data[:5]:
            evidence.append({"type": "deployment", "version": d["version"], "status": d["status"], "timestamp": d["timestamp"]})

        await emit_step("telemetry_collected", {
            "logs_count": len(logs_data),
            "metrics_count": len(metrics_data),
            "traces_count": len(traces_data),
            "deployments_count": len(deployments_data),
        })

        return {
            **state,
            "logs": logs_data,
            "metrics": metrics_data,
            "traces": traces_data,
            "deployments": deployments_data,
            "evidence": evidence,
        }

    async def timeline_node(state: IncidentState) -> IncidentState:
        timeline_raw: list[dict[str, Any]] = []

        for d in state.get("deployments", []):
            timeline_raw.append({
                "timestamp": d["timestamp"],
                "source": "deployments",
                "event": f"Deployment {d['version']} published with status {d['status']}",
                "severity": "info",
            })

        for log in state.get("logs", []):
            sev = "critical" if log["level"] in ("ERROR", "FATAL", "CRITICAL") else "warning" if log["level"] == "WARN" else "info"
            timeline_raw.append({
                "timestamp": log["timestamp"],
                "source": "logs",
                "event": log["message"],
                "severity": sev,
            })

        for m in state.get("metrics", []):
            if "5xx" in m["name"] or "error" in m["name"] or m["value"] > 500:
                timeline_raw.append({
                    "timestamp": m["timestamp"],
                    "source": "metrics",
                    "event": f"Metric {m['name']} recorded anomaly value {m['value']}",
                    "severity": "warning",
                })

        for t in state.get("traces", []):
            if t["status"] == "ERROR" or t["duration"] > 1.0:
                timeline_raw.append({
                    "timestamp": t["timestamp"],
                    "source": "traces",
                    "event": f"Trace {t['trace_id']} latency={t['duration']}s status={t['status']}",
                    "severity": "critical" if t["status"] == "ERROR" else "warning",
                })

        # Sort timeline chronologically
        timeline_raw.sort(key=lambda x: x["timestamp"])

        await emit_step("timeline_correlated", {
            "total_timeline_events": len(timeline_raw)
        })

        return {
            **state,
            "timeline": timeline_raw,
        }

    async def rag_node(state: IncidentState) -> IncidentState:
        # Build dense query from extracted symptoms
        error_logs = [log["message"] for log in state.get("logs", []) if log.get("level") in ("ERROR", "CRITICAL", "WARN")][:5]
        metric_names = [m["name"] for m in state.get("metrics", [])][:5]
        query_parts = error_logs + metric_names + [state.get("title", ""), state.get("service", "")]
        query = " ".join([p for p in query_parts if p]) or "database connection pool timeout latency"

        docs = retriever.search(query=query, k=4)

        await emit_step("rag_completed", {
            "matched_runbooks": [d["name"] for d in docs],
            "top_score": docs[0]["score"] if docs else 0.0,
        })

        return {
            **state,
            "retrieved_documents": docs,
        }

    async def rca_node(state: IncidentState) -> IncidentState:
        provider = get_provider()
        context = {
            "incident_id": state["incident_id"],
            "service": state["service"],
            "environment": state.get("environment", "production"),
            "title": state.get("title", ""),
        }

        result: StructuredInvestigationResult = await provider.investigate(
            service=state["service"],
            severity=state["severity"],
            evidence=state.get("evidence", []),
            timeline=state.get("timeline", []),
            runbooks=state.get("retrieved_documents", []),
            context=context,
        )

        await emit_step("rca_completed", {
            "root_cause": result.root_cause.title,
            "confidence": result.root_cause.confidence,
        })

        return {
            **state,
            "root_cause": result.root_cause.model_dump(),
            "confidence": result.root_cause.confidence,
            "hypotheses": [h for h in result.hypotheses],
            "alternative_causes": [a.model_dump() for a in result.alternative_causes],
            "recommendations": result.recommendations,
            "remediation_plan": result.remediation.model_dump(),
            "verification_plan": [v.model_dump() for v in result.verification_plan],
            "structured_result": result.model_dump(),
        }

    # Construct StateGraph
    workflow = StateGraph(IncidentState)
    workflow.add_node("context", context_node)
    workflow.add_node("telemetry", telemetry_node)
    workflow.add_node("timeline", timeline_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("rca", rca_node)

    workflow.set_entry_point("context")
    workflow.add_edge("context", "telemetry")
    workflow.add_edge("telemetry", "timeline")
    workflow.add_edge("timeline", "rag")
    workflow.add_edge("rag", "rca")
    workflow.add_edge("rca", END)

    return workflow.compile()
