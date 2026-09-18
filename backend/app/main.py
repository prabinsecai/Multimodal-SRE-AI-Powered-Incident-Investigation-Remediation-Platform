from datetime import datetime, timezone, timedelta
import json
import time
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from sqlalchemy import select, desc
from app.core.db import Base, engine, get_db, Session
from app.models.models import (
    Service, Incident, IncidentEvent, Log, Metric, Trace,
    Hypothesis, RemediationAction, AgentRun, AuditLog, DeploymentEvent
)
from app.schemas.api import (
    Login, Token, LogIn, MetricIn, TraceIn, DeploymentIn, IncidentCreate,
    KnowledgeSearchRequest, KnowledgeSearchResult
)
from app.services.auth import ensure_admin, login
from app.api.deps import current_user, require_roles
from app.agents.workflow import build_workflow
from app.rag.hybrid import HybridRetriever, load_runbooks
from app.tools.simulator import MockKubernetesProvider
from app.workers.tasks import investigate_incident
from app.workers.celery_app import celery_app
from app.anomaly.service import detect_metric_anomaly
from app.core.config import settings

app = FastAPI(
    title="MultiModal-SRE",
    version="1.0.0",
    description="Autonomous multimodal SRE incident investigation, telemetry correlation and safe remediation platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sim = MockKubernetesProvider()

# Prometheus Metrics
REQUESTS = Counter("sre_http_requests_total", "Total HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("sre_http_request_duration_seconds", "HTTP request latency in seconds", ["path"])
ANOMALY_GAUGE = Gauge("sre_active_anomalies_total", "Active detected anomalies count")
INVESTIGATION_DURATION = Histogram("sre_investigation_duration_seconds", "Investigation agent execution duration in seconds")

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        dur = time.perf_counter() - start_time
        path = request.url.path
        REQUESTS.labels(request.method, path, str(status_code)).inc()
        LATENCY.labels(path).observe(dur)

async def seed_services_if_empty():
    async with Session() as db:
        existing = (await db.execute(select(Service))).scalars().all()
        if not existing:
            default_services = [
                Service(name="payment-api", environment="production", owner="payments-team", status="healthy"),
                Service(name="order-api", environment="production", owner="orders-team", status="healthy"),
                Service(name="auth-api", environment="production", owner="security-team", status="healthy"),
                Service(name="notification-worker", environment="production", owner="notifications-team", status="healthy"),
                Service(name="inventory-service", environment="production", owner="inventory-team", status="healthy"),
            ]
            db.add_all(default_services)
            await db.commit()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async for db in get_db():
        await ensure_admin(db)
        break
    await seed_services_if_empty()

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "version": app.version,
        "execution_mode": settings.execution_mode,
        "model_provider": settings.model_provider,
        "model_name": settings.model_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ================= AUTHENTICATION =================
@app.post("/api/v1/auth/login", response_model=Token)
async def auth_login(x: Login, db=Depends(get_db)):
    token = await login(db, x.email, x.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return Token(access_token=token)

@app.get("/api/v1/me")
async def get_me(u: dict = Depends(current_user)):
    return u

# ================= SERVICES =================
@app.get("/api/v1/services")
async def list_services(_: dict = Depends(current_user), db=Depends(get_db)):
    services = (await db.execute(select(Service).order_by(Service.name))).scalars().all()
    # Enrich with live simulator metrics
    results = []
    for s in services:
        sim_health = sim.health(s.name)
        results.append({
            "id": s.id,
            "name": s.name,
            "environment": s.environment,
            "owner": s.owner,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
            "version": sim_health.get("version", "v1.0.0"),
            "error_rate": sim_health.get("error_rate", 0.001),
            "latency_ms": sim_health.get("latency_ms", 50.0),
            "replicas": sim_health.get("replicas", 3),
        })
    return results

@app.get("/api/v1/services/{name}/health")
async def service_health(name: str, _: dict = Depends(current_user)):
    return sim.health(name)

# ================= INCIDENTS =================
@app.get("/api/v1/incidents")
async def list_incidents(
    status_filter: str | None = Query(None, alias="status"),
    severity: str | None = None,
    service_id: int | None = None,
    _: dict = Depends(current_user),
    db=Depends(get_db)
):
    query = select(Incident).order_by(desc(Incident.id))
    if status_filter:
        query = query.where(Incident.status == status_filter)
    if severity:
        query = query.where(Incident.severity == severity)
    if service_id:
        query = query.where(Incident.service_id == service_id)

    incidents = (await db.execute(query)).scalars().all()
    results = []
    for inc in incidents:
        svc = await db.get(Service, inc.service_id)
        results.append({
            "id": inc.id,
            "title": inc.title,
            "service_id": inc.service_id,
            "service_name": svc.name if svc else "unknown",
            "severity": inc.severity,
            "status": inc.status,
            "detected_at": inc.detected_at.isoformat() if inc.detected_at else None,
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
            "root_cause": inc.root_cause,
            "confidence": inc.confidence,
            "created_at": inc.created_at.isoformat(),
        })
    return results

@app.post("/api/v1/incidents")
async def create_incident(
    x: IncidentCreate,
    u: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")),
    db=Depends(get_db)
):
    svc = await db.get(Service, x.service_id)
    if not svc:
        raise HTTPException(404, "Service not found")

    inc = Incident(
        title=x.title,
        service_id=x.service_id,
        severity=x.severity,
        status="OPEN",
        detected_at=datetime.now(timezone.utc),
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)

    db.add(IncidentEvent(
        incident_id=inc.id,
        event_type="incident_created",
        source="manual",
        payload={"created_by": u.get("email"), "title": inc.title}
    ))
    db.add(AuditLog(
        user_id=int(u["sub"]),
        action="create_incident",
        resource_type="incident",
        resource_id=str(inc.id),
        metadata_={"title": inc.title, "severity": inc.severity}
    ))
    await db.commit()
    return inc

@app.get("/api/v1/incidents/{iid}")
async def get_incident(iid: int, _: dict = Depends(current_user), db=Depends(get_db)):
    inc = await db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")

    svc = await db.get(Service, inc.service_id)
    events = (await db.execute(select(IncidentEvent).where(IncidentEvent.incident_id == iid).order_by(IncidentEvent.timestamp))).scalars().all()
    hypotheses = (await db.execute(select(Hypothesis).where(Hypothesis.incident_id == iid))).scalars().all()
    remediations = (await db.execute(select(RemediationAction).where(RemediationAction.incident_id == iid).order_by(desc(RemediationAction.id)))).scalars().all()
    agent_runs = (await db.execute(select(AgentRun).where(AgentRun.incident_id == iid).order_by(desc(AgentRun.id)))).scalars().all()

    latest_run_output = agent_runs[0].output if agent_runs else {}

    return {
        "id": inc.id,
        "title": inc.title,
        "service_id": inc.service_id,
        "service_name": svc.name if svc else "unknown",
        "environment": svc.environment if svc else "production",
        "severity": inc.severity,
        "status": inc.status,
        "detected_at": inc.detected_at.isoformat() if inc.detected_at else None,
        "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
        "root_cause": inc.root_cause,
        "confidence": inc.confidence,
        "created_at": inc.created_at.isoformat(),
        "events": [{
            "id": e.id,
            "event_type": e.event_type,
            "source": e.source,
            "payload": e.payload,
            "timestamp": e.timestamp.isoformat()
        } for e in events],
        "hypotheses": [{
            "id": h.id,
            "hypothesis": h.hypothesis,
            "evidence": h.evidence,
            "confidence": h.confidence,
            "created_at": h.created_at.isoformat()
        } for h in hypotheses],
        "remediations": [{
            "id": r.id,
            "action": r.action,
            "risk_level": r.risk_level,
            "approval_status": r.approval_status,
            "execution_status": r.execution_status,
            "result": r.result,
            "created_at": r.created_at.isoformat()
        } for r in remediations],
        "structured_investigation": latest_run_output,
    }

async def _execute_investigation(iid: int, db):
    inc = await db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")

    started = time.perf_counter()
    inc.status = "INVESTIGATING"
    await db.commit()

    workflow = build_workflow()
    state = await workflow.ainvoke({"incident_id": iid})
    duration = time.perf_counter() - started
    INVESTIGATION_DURATION.observe(duration)

    # Extract results
    root_cause_data = state.get("root_cause", {})
    root_cause_title = root_cause_data.get("title") if isinstance(root_cause_data, dict) else str(root_cause_data)
    confidence = float(state.get("confidence", 0.85))

    inc.root_cause = root_cause_title
    inc.confidence = confidence
    inc.status = "AWAITING_APPROVAL"

    # Save hypotheses
    for h in state.get("hypotheses", []):
        db.add(Hypothesis(
            incident_id=iid,
            hypothesis=h.get("hypothesis", ""),
            evidence=h.get("evidence", []),
            confidence=float(h.get("confidence", 0.8))
        ))

    # Save remediation action
    plan = state.get("remediation_plan", {"action": "observe_and_escalate", "risk": "low"})
    action_record = RemediationAction(
        incident_id=iid,
        action=plan.get("action", "observe_and_escalate"),
        risk_level=plan.get("risk", "low").upper(),
        approval_status="PENDING",
        execution_status="NOT_STARTED"
    )
    db.add(action_record)

    # Save Agent Run
    structured = state.get("structured_result", state)
    agent_run = AgentRun(
        incident_id=iid,
        agent_name="multimodal-investigator",
        input={"incident_id": iid},
        output=structured,
        duration=duration,
        status="SUCCEEDED"
    )
    db.add(agent_run)

    # Save IncidentEvent
    db.add(IncidentEvent(
        incident_id=iid,
        event_type="investigation_complete",
        source="langgraph",
        payload={
            "root_cause": inc.root_cause,
            "confidence": inc.confidence,
            "duration_seconds": round(duration, 2),
            "runbooks_cited": [d.get("name") for d in state.get("retrieved_documents", [])]
        }
    ))

    await db.commit()
    await db.refresh(action_record)

    return {
        "incident": inc,
        "structured_investigation": structured,
        "hypotheses": state.get("hypotheses", []),
        "remediation": action_record,
        "evidence": state.get("evidence", []),
        "timeline": state.get("timeline", []),
        "retrieved_documents": state.get("retrieved_documents", []),
    }

@app.post("/api/v1/incidents/{iid}/investigate")
async def investigate(
    iid: int,
    _: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")),
    db=Depends(get_db)
):
    return await _execute_investigation(iid, db)

@app.post("/api/v1/incidents/{iid}/investigate/async")
async def investigate_async(
    iid: int,
    _: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")),
    db=Depends(get_db)
):
    inc = await db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    inc.status = "INVESTIGATING"
    await db.commit()
    task = investigate_incident.delay(iid)
    return {"task_id": task.id, "status": "QUEUED", "incident_id": iid}

@app.get("/api/v1/tasks/{task_id}")
async def task_status(task_id: str, _: dict = Depends(current_user)):
    r = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": r.status,
        "result": r.result if r.ready() else None
    }

@app.get("/api/v1/incidents/{iid}/hypotheses")
async def get_hypotheses(iid: int, _: dict = Depends(current_user), db=Depends(get_db)):
    return (await db.execute(select(Hypothesis).where(Hypothesis.incident_id == iid))).scalars().all()

@app.get("/api/v1/incidents/{iid}/events")
async def get_events(iid: int, _: dict = Depends(current_user), db=Depends(get_db)):
    return (await db.execute(select(IncidentEvent).where(IncidentEvent.incident_id == iid).order_by(IncidentEvent.timestamp))).scalars().all()

# ================= REMEDIATION & HUMAN APPROVAL =================
@app.post("/api/v1/incidents/{iid}/remediation/{aid}/approve")
async def approve_remediation(
    iid: int,
    aid: int,
    u: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")),
    db=Depends(get_db)
):
    a = await db.get(RemediationAction, aid)
    if not a or a.incident_id != iid:
        raise HTTPException(404, "Action not found for this incident")
    if a.approval_status != "PENDING":
        raise HTTPException(409, f"Action is already {a.approval_status}")

    inc = await db.get(Incident, iid)
    svc = await db.get(Service, inc.service_id) if inc else None
    service_name = svc.name if svc else "payment-api"

    a.approval_status = "APPROVED"
    a.execution_status = "RUNNING"

    # Execute simulation based on action
    if a.action == "rollback_deployment":
        res = sim.rollback_service(service_name, "v1.8.2")
    elif a.action == "scale_replicas":
        res = sim.scale_service(service_name, 5)
    elif a.action == "restart_service":
        res = sim.restart_service(service_name)
    elif a.action == "flush_connections":
        res = sim.flush_connections(service_name)
    else:
        res = {"mode": "simulation", "action": a.action, "status": "executed", "reason": "observe_and_escalate"}

    a.result = res
    a.execution_status = "SUCCEEDED"

    if inc:
        inc.status = "RESOLVED"
        inc.resolved_at = datetime.now(timezone.utc)

    # Verification health check
    verification_health = sim.health(service_name)

    db.add(AuditLog(
        user_id=int(u["sub"]),
        action="approve_and_execute_remediation",
        resource_type="remediation",
        resource_id=str(aid),
        metadata_={"action": a.action, "result": res, "service": service_name}
    ))
    db.add(IncidentEvent(
        incident_id=iid,
        event_type="remediation_executed",
        source="simulator",
        payload={"action": a.action, "result": res, "verification": verification_health}
    ))

    await db.commit()
    return {
        "action": a,
        "verification": verification_health,
        "incident_status": inc.status if inc else "RESOLVED"
    }

@app.post("/api/v1/incidents/{iid}/remediation/{aid}/reject")
async def reject_remediation(
    iid: int,
    aid: int,
    u: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")),
    db=Depends(get_db)
):
    a = await db.get(RemediationAction, aid)
    if not a or a.incident_id != iid:
        raise HTTPException(404, "Action not found")

    a.approval_status = "REJECTED"
    a.execution_status = "CANCELLED"

    db.add(AuditLog(
        user_id=int(u["sub"]),
        action="reject_remediation",
        resource_type="remediation",
        resource_id=str(aid),
        metadata_={"action": a.action}
    ))
    db.add(IncidentEvent(
        incident_id=iid,
        event_type="remediation_rejected",
        source="human_operator",
        payload={"rejected_by": u.get("email"), "action": a.action}
    ))

    await db.commit()
    return a

# ================= TELEMETRY INGESTION =================
@app.post("/api/v1/logs/ingest")
async def ingest_log(x: LogIn, _: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")), db=Depends(get_db)):
    # Template extraction: simple tokenized pattern
    template = x.message.split(":")[0] if ":" in x.message else x.message[:80]
    log_obj = Log(
        service=x.service,
        timestamp=x.timestamp,
        level=x.level,
        message=x.message,
        template=template,
        trace_id=x.trace_id,
        correlation_id=x.correlation_id,
    )
    db.add(log_obj)
    await db.commit()
    return {"accepted": 1, "id": log_obj.id}

@app.post("/api/v1/logs/batch")
async def ingest_logs_batch(xs: list[LogIn], _: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")), db=Depends(get_db)):
    for x in xs:
        template = x.message.split(":")[0] if ":" in x.message else x.message[:80]
        db.add(Log(
            service=x.service,
            timestamp=x.timestamp,
            level=x.level,
            message=x.message,
            template=template,
            trace_id=x.trace_id,
            correlation_id=x.correlation_id,
        ))
    await db.commit()
    return {"accepted": len(xs)}

@app.post("/api/v1/metrics/ingest")
async def ingest_metric(x: MetricIn, _: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")), db=Depends(get_db)):
    metric_obj = Metric(
        service=x.service,
        metric_name=x.metric_name,
        value=x.value,
        timestamp=x.timestamp,
        labels=x.labels,
    )
    db.add(metric_obj)
    await db.commit()

    # Trigger anomaly detection pipeline
    anomaly_res = await detect_metric_anomaly(
        db,
        service_name=x.service,
        metric_name=x.metric_name,
        threshold=settings.anomaly_threshold
    )
    if anomaly_res and anomaly_res.get("anomaly_detected"):
        ANOMALY_GAUGE.inc()

    return {"accepted": 1, "anomaly": anomaly_res}

@app.post("/api/v1/traces/ingest")
async def ingest_trace(x: TraceIn, _: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")), db=Depends(get_db)):
    trace_obj = Trace(
        service=x.service,
        trace_id=x.trace_id,
        span_id=x.span_id,
        duration=x.duration,
        status=x.status,
        timestamp=x.timestamp,
    )
    db.add(trace_obj)
    await db.commit()
    return {"accepted": 1}

@app.post("/api/v1/deployments/ingest")
async def ingest_deployment(x: DeploymentIn, _: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")), db=Depends(get_db)):
    deploy_obj = DeploymentEvent(
        service=x.service,
        version=x.version,
        timestamp=x.timestamp,
        status=x.status,
        metadata_=x.metadata,
    )
    db.add(deploy_obj)
    await db.commit()
    return {"accepted": 1}

# ================= TELEMETRY BROWSING =================
@app.get("/api/v1/logs")
async def list_logs(
    service: str | None = None,
    level: str | None = None,
    limit: int = 100,
    _: dict = Depends(current_user),
    db=Depends(get_db)
):
    q = select(Log).order_by(desc(Log.timestamp)).limit(limit)
    if service:
        q = q.where(Log.service == service)
    if level:
        q = q.where(Log.level == level)
    return (await db.execute(q)).scalars().all()

@app.get("/api/v1/metrics")
async def list_metrics(
    service: str | None = None,
    metric_name: str | None = None,
    limit: int = 200,
    _: dict = Depends(current_user),
    db=Depends(get_db)
):
    q = select(Metric).order_by(desc(Metric.timestamp)).limit(limit)
    if service:
        q = q.where(Metric.service == service)
    if metric_name:
        q = q.where(Metric.metric_name == metric_name)
    return (await db.execute(q)).scalars().all()

@app.get("/api/v1/traces")
async def list_traces(
    service: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = 100,
    _: dict = Depends(current_user),
    db=Depends(get_db)
):
    q = select(Trace).order_by(desc(Trace.timestamp)).limit(limit)
    if service:
        q = q.where(Trace.service == service)
    if status_filter:
        q = q.where(Trace.status == status_filter)
    return (await db.execute(q)).scalars().all()

@app.get("/api/v1/deployments")
async def list_deployments(
    service: str | None = None,
    limit: int = 100,
    _: dict = Depends(current_user),
    db=Depends(get_db)
):
    q = select(DeploymentEvent).order_by(desc(DeploymentEvent.timestamp)).limit(limit)
    if service:
        q = q.where(DeploymentEvent.service == service)
    return (await db.execute(q)).scalars().all()

@app.get("/api/v1/audit")
async def list_audit_logs(limit: int = 300, _: dict = Depends(require_roles("ADMIN")), db=Depends(get_db)):
    return (await db.execute(select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit))).scalars().all()

# ================= KNOWLEDGE BASE (RAG) =================
@app.get("/api/v1/knowledge/runbooks")
async def list_runbooks(_: dict = Depends(current_user)):
    docs = load_runbooks()
    return [{"name": d["name"], "title": d.get("title", d["name"]), "snippet": d["text"][:300]} for d in docs]

@app.post("/api/v1/knowledge/search", response_model=list[KnowledgeSearchResult])
async def search_knowledge(x: KnowledgeSearchRequest, _: dict = Depends(current_user)):
    retriever = HybridRetriever(load_runbooks())
    hits = retriever.search(x.query, k=x.limit)
    return [KnowledgeSearchResult(**h) for h in hits]

# ================= DEMO SCENARIOS =================
@app.post("/api/v1/demo/incidents/database-timeout")
async def demo_database_timeout(_: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")), db=Depends(get_db)):
    svc = (await db.execute(select(Service).where(Service.name == "payment-api"))).scalar_one_or_none()
    if not svc:
        svc = Service(name="payment-api", environment="production", owner="payments-team", status="degraded")
        db.add(svc)
        await db.commit()
        await db.refresh(svc)
    else:
        svc.status = "degraded"

    now = datetime.now(timezone.utc)
    t_minus_5 = now - timedelta(minutes=5)
    t_minus_2 = now - timedelta(minutes=2)

    # 1. Deployment 6 minutes ago
    db.add(DeploymentEvent(
        service="payment-api",
        version="v1.8.3",
        timestamp=now - timedelta(minutes=6),
        status="SUCCESS",
        metadata_={"author": "alex@company.com", "commit": "f9a82c1", "message": "Add batch checkout optimizations"}
    ))

    # 2. Historical baseline metrics
    for i in range(15, 5, -1):
        t_hist = now - timedelta(minutes=i)
        db.add(Metric(service="payment-api", metric_name="db_connection_utilization", value=0.35 + (i % 3)*0.02, timestamp=t_hist))
        db.add(Metric(service="payment-api", metric_name="http_5xx_rate", value=0.001, timestamp=t_hist))
        db.add(Metric(service="payment-api", metric_name="latency_ms", value=85.0 + (i % 4)*2.0, timestamp=t_hist))

    # 3. Anomaly metrics post deployment
    db.add_all([
        Metric(service="payment-api", metric_name="db_connection_utilization", value=0.98, timestamp=t_minus_2),
        Metric(service="payment-api", metric_name="http_5xx_rate", value=0.18, timestamp=t_minus_2),
        Metric(service="payment-api", metric_name="latency_ms", value=1850.0, timestamp=t_minus_2),
        Metric(service="payment-api", metric_name="db_connection_utilization", value=0.99, timestamp=now),
        Metric(service="payment-api", metric_name="http_5xx_rate", value=0.24, timestamp=now),
        Metric(service="payment-api", metric_name="latency_ms", value=2200.0, timestamp=now),
    ])

    # 4. Error Logs
    db.add_all([
        Log(service="payment-api", timestamp=t_minus_5, level="WARN", message="Connection pool wait queue depth approaching limit (45/50)"),
        Log(service="payment-api", timestamp=t_minus_2, level="ERROR", message="database timeout acquiring connection from pool after 30000ms", template="database timeout acquiring connection from pool"),
        Log(service="payment-api", timestamp=now, level="ERROR", message="asyncpg.exceptions.TooManyConnectionsError: remaining connection slots are reserved for non-replication superuser connections", template="TooManyConnectionsError"),
        Log(service="payment-api", timestamp=now, level="CRITICAL", message="HTTP 504 Gateway Timeout: /v1/checkout request failed due to database connection timeout", template="HTTP 504 Gateway Timeout"),
    ])

    # 5. Degraded Traces
    db.add_all([
        Trace(service="payment-api", trace_id=f"trace-checkout-{int(now.timestamp())}-1", span_id="span-db-acquire", duration=1.85, status="ERROR", timestamp=t_minus_2),
        Trace(service="payment-api", trace_id=f"trace-checkout-{int(now.timestamp())}-2", span_id="span-db-acquire", duration=2.40, status="ERROR", timestamp=now),
    ])

    # 6. Create Incident
    inc = Incident(
        title="Payment API Database Connection Pool Saturation & 504 Spikes",
        service_id=svc.id,
        severity="SEV-1",
        status="OPEN",
        detected_at=now,
        confidence=0.92,
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)

    db.add(IncidentEvent(
        incident_id=inc.id,
        event_type="incident_triggered",
        source="anomaly_detector",
        payload={"service": "payment-api", "anomaly": "db_connection_utilization > 95%", "severity": "SEV-1"}
    ))
    await db.commit()

    return {"incident_id": inc.id, "scenario": "database_timeout", "service": "payment-api"}

@app.post("/api/v1/demo/incidents/redis-failure")
async def demo_redis_failure(_: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")), db=Depends(get_db)):
    svc = (await db.execute(select(Service).where(Service.name == "order-api"))).scalar_one_or_none()
    if not svc:
        svc = Service(name="order-api", environment="production", owner="orders-team", status="degraded")
        db.add(svc)
        await db.commit()
        await db.refresh(svc)

    now = datetime.now(timezone.utc)
    db.add_all([
        Log(service="order-api", timestamp=now, level="ERROR", message="redis.exceptions.ConnectionError: Error while reading from socket: connection timed out", template="redis connection timed out"),
        Metric(service="order-api", metric_name="redis_command_latency_ms", value=145.0, timestamp=now),
        Metric(service="order-api", metric_name="cache_miss_rate", value=0.88, timestamp=now),
        Trace(service="order-api", trace_id=f"trace-order-{int(now.timestamp())}", span_id="redis-get", duration=1.2, status="ERROR", timestamp=now),
    ])
    inc = Incident(
        title="Order API Redis Connection Timeout & Cache Degraded",
        service_id=svc.id,
        severity="SEV-2",
        status="OPEN",
        detected_at=now,
        confidence=0.88,
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)
    return {"incident_id": inc.id, "scenario": "redis_failure", "service": "order-api"}

@app.post("/api/v1/demo/incidents/k8s-crashloop")
async def demo_k8s_crashloop(_: dict = Depends(require_roles("ADMIN", "SRE_ENGINEER")), db=Depends(get_db)):
    svc = (await db.execute(select(Service).where(Service.name == "auth-api"))).scalar_one_or_none()
    if not svc:
        svc = Service(name="auth-api", environment="production", owner="security-team", status="degraded")
        db.add(svc)
        await db.commit()
        await db.refresh(svc)

    now = datetime.now(timezone.utc)
    db.add_all([
        DeploymentEvent(service="auth-api", version="v3.0.5", timestamp=now - timedelta(minutes=4), status="SUCCESS", metadata_={"author": "devops@company.com"}),
        Log(service="auth-api", timestamp=now, level="FATAL", message="Container terminated with exit code 137 (OOMKilled): memory limit exceeded (512Mi)", template="OOMKilled exit code 137"),
        Metric(service="auth-api", metric_name="k8s_pod_restart_count", value=8.0, timestamp=now),
        Metric(service="auth-api", metric_name="pod_ready_status", value=0.0, timestamp=now),
    ])
    inc = Incident(
        title="Auth API Pod CrashLoopBackOff (OOMKilled Exit Code 137)",
        service_id=svc.id,
        severity="SEV-1",
        status="OPEN",
        detected_at=now,
        confidence=0.91,
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)
    return {"incident_id": inc.id, "scenario": "k8s_crashloop", "service": "auth-api"}

# ================= LIVE WEBSOCKET AGENT INVESTIGATION =================
@app.websocket("/ws/incidents/{iid}")
async def websocket_investigate(ws: WebSocket, iid: int, token: str | None = Query(default=None)):
    await ws.accept()
    if not token:
        await ws.send_json({"event": "error", "message": "Missing authentication token"})
        await ws.close(code=1008)
        return

    try:
        from app.core.security import decode_token
        decode_token(token)
    except Exception:
        await ws.send_json({"event": "error", "message": "Invalid authentication token"})
        await ws.close(code=1008)
        return

    async def step_notifier(step_name: str, payload: dict[str, Any]):
        try:
            await ws.send_json({
                "event": "step_update",
                "step": step_name,
                "incident_id": iid,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception:
            pass

    # Send initial connected status
    await ws.send_json({
        "event": "connected",
        "incident_id": iid,
        "message": f"Connected to investigation stream for incident #{iid}"
    })

    try:
        while True:
            data_text = await ws.receive_text()
            try:
                msg = json.loads(data_text)
            except Exception:
                msg = {"action": data_text}

            action = msg.get("action")
            if action == "start_investigation":
                await ws.send_json({"event": "investigation_started", "incident_id": iid})
                async with Session() as db:
                    workflow = build_workflow(step_callback=step_notifier)
                    state = await workflow.ainvoke({"incident_id": iid})

                    # Update incident in DB
                    inc = await db.get(Incident, iid)
                    if inc:
                        root_cause_obj = state.get("root_cause", {})
                        inc.root_cause = root_cause_obj.get("title") if isinstance(root_cause_obj, dict) else str(root_cause_obj)
                        inc.confidence = float(state.get("confidence", 0.85))
                        inc.status = "AWAITING_APPROVAL"

                        plan = state.get("remediation_plan", {"action": "observe_and_escalate", "risk": "low"})
                        action_rec = RemediationAction(
                            incident_id=iid,
                            action=plan.get("action", "observe_and_escalate"),
                            risk_level=plan.get("risk", "low").upper(),
                            approval_status="PENDING",
                            execution_status="NOT_STARTED"
                        )
                        db.add(action_rec)
                        await db.commit()

                    await ws.send_json({
                        "event": "investigation_finished",
                        "incident_id": iid,
                        "result": state.get("structured_result", state),
                        "status": "AWAITING_APPROVAL"
                    })

            elif action == "ping":
                await ws.send_json({"event": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        pass
