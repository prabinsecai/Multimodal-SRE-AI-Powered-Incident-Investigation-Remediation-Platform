import pytest
from app.agents.llm import DeterministicEvidenceReasoner
from app.schemas.api import StructuredInvestigationResult

@pytest.mark.asyncio
async def test_deterministic_evidence_reasoner():
    reasoner = DeterministicEvidenceReasoner()
    evidence = [
        {"type": "log", "detail": "database timeout acquiring connection from pool"},
        {"type": "metric", "name": "db_connection_utilization", "value": 0.98},
        {"type": "metric", "name": "http_5xx_rate", "value": 0.18},
        {"type": "deployment", "version": "v1.8.3", "status": "SUCCESS"}
    ]
    timeline = [
        {"timestamp": "2026-09-01T10:00:00Z", "source": "deployments", "event": "Deployment v1.8.3"},
        {"timestamp": "2026-09-01T10:05:00Z", "source": "logs", "event": "database timeout acquiring connection from pool"}
    ]
    runbooks = [
        {"name": "postgres-connection-pool.md", "snippet": "PostgreSQL connection pool exhaustion"}
    ]

    result = await reasoner.investigate(
        service="payment-api",
        severity="SEV-1",
        evidence=evidence,
        timeline=timeline,
        runbooks=runbooks,
        context={"incident_id": 1}
    )

    assert isinstance(result, StructuredInvestigationResult)
    assert "PostgreSQL Connection Pool Exhaustion" in result.root_cause.title
    assert result.root_cause.confidence >= 0.85
    assert len(result.alternative_causes) > 0
    assert result.remediation.action in ("rollback_deployment", "flush_connections")
    assert len(result.verification_plan) > 0
