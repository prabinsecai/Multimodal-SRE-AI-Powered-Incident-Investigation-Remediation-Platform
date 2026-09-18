from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

# Auth schemas
class Login(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime

# Telemetry ingestion schemas
class LogIn(BaseModel):
    service: str = Field(min_length=1, max_length=100)
    timestamp: datetime
    level: str = "INFO"
    message: str = Field(min_length=1, max_length=10000)
    trace_id: str | None = None
    correlation_id: str | None = None

class MetricIn(BaseModel):
    service: str
    metric_name: str
    value: float
    timestamp: datetime
    labels: dict[str, str] = Field(default_factory=dict)

class TraceIn(BaseModel):
    service: str
    trace_id: str
    span_id: str
    duration: float = Field(ge=0)
    status: str = "OK"
    timestamp: datetime

class DeploymentIn(BaseModel):
    service: str
    version: str
    timestamp: datetime
    status: str = "SUCCESS"
    metadata: dict[str, Any] = Field(default_factory=dict)

# Incident schemas
class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    service_id: int
    severity: str = "SEV-2"

class ActionDecision(BaseModel):
    approved: bool
    reason: str | None = None

# Structured Investigation Output Schemas (Prompt Spec #5)
class RootCauseDetail(BaseModel):
    title: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    primary_evidence: list[str] = Field(default_factory=list)

class AlternativeCause(BaseModel):
    hypothesis: str
    probability: str = "low"
    reason_rejected: str

class RemediationPlan(BaseModel):
    action: str
    risk: str = "low"
    requires_approval: bool = True
    description: str = ""
    rollback_target: str | None = None

class VerificationStep(BaseModel):
    step: str
    metric_or_signal: str
    target_condition: str

class TimelineEntry(BaseModel):
    timestamp: str
    source: str
    event: str
    severity: str = "info"

class StructuredInvestigationResult(BaseModel):
    summary: str
    severity: str
    affected_service: str
    observations: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    root_cause: RootCauseDetail
    alternative_causes: list[AlternativeCause] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    remediation: RemediationPlan
    verification_plan: list[VerificationStep] = Field(default_factory=list)
    status: str = "investigated"
    retrieved_documents: list[dict[str, Any]] = Field(default_factory=list)

# Knowledge search schemas
class KnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = 5

class KnowledgeSearchResult(BaseModel):
    name: str
    score: float
    text: str
    snippet: str = ""
