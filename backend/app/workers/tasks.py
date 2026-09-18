import asyncio
import time
from .celery_app import celery_app
from app.core.db import Session
from app.models.models import Incident, Hypothesis, RemediationAction, AgentRun, IncidentEvent
from app.agents.workflow import build_workflow

async def _run_async_investigation(incident_id: int):
    started_at = time.perf_counter()
    async with Session() as db:
        inc = await db.get(Incident, incident_id)
        if not inc:
            return {"error": "Incident not found", "incident_id": incident_id}

        inc.status = "INVESTIGATING"
        db.add(IncidentEvent(
            incident_id=incident_id,
            event_type="investigation_started",
            source="celery_worker",
            payload={"message": "Background worker started investigation workflow"}
        ))
        await db.commit()

    # Execute LangGraph workflow
    workflow = build_workflow()
    state = await workflow.ainvoke({"incident_id": incident_id})

    async with Session() as db:
        inc = await db.get(Incident, incident_id)
        if inc:
            root_cause_obj = state.get("root_cause", {})
            inc.root_cause = root_cause_obj.get("title") if isinstance(root_cause_obj, dict) else str(root_cause_obj)
            inc.confidence = float(state.get("confidence", 0.85))
            inc.status = "AWAITING_APPROVAL"

            # Save hypotheses
            for h in state.get("hypotheses", []):
                hyp = Hypothesis(
                    incident_id=incident_id,
                    hypothesis=h.get("hypothesis", ""),
                    evidence=h.get("evidence", []),
                    confidence=float(h.get("confidence", 0.8))
                )
                db.add(hyp)

            # Save remediation action
            plan = state.get("remediation_plan", {"action": "observe_and_escalate", "risk": "low"})
            action = RemediationAction(
                incident_id=incident_id,
                action=plan.get("action", "observe_and_escalate"),
                risk_level=plan.get("risk", "low").upper(),
                approval_status="PENDING",
                execution_status="NOT_STARTED"
            )
            db.add(action)

            # Save agent run record
            duration = time.perf_counter() - started_at
            agent_run = AgentRun(
                incident_id=incident_id,
                agent_name="multimodal-investigator",
                input={"incident_id": incident_id},
                output=state.get("structured_result", state),
                duration=duration,
                status="SUCCEEDED"
            )
            db.add(agent_run)

            # Save completion event
            db.add(IncidentEvent(
                incident_id=incident_id,
                event_type="investigation_complete",
                source="langgraph",
                payload={
                    "root_cause": inc.root_cause,
                    "confidence": inc.confidence,
                    "duration_seconds": round(duration, 2),
                    "retrieved_runbooks": [d.get("name") for d in state.get("retrieved_documents", [])]
                }
            ))

            await db.commit()

    return state.get("structured_result", state)

@celery_app.task(name='investigate_incident')
def investigate_incident(incident_id: int):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_async_investigation(incident_id))
    finally:
        loop.close()
