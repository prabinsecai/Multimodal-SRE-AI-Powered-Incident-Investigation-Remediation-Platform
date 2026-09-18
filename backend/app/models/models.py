from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, DateTime, Float, Text, ForeignKey, Integer, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="VIEWER", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    environment: Mapped[str] = mapped_column(String(50), default="production", nullable=False)
    owner: Mapped[str] = mapped_column(String(100), default="sre-team", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="healthy", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    incidents: Mapped[list["Incident"]] = relationship("Incident", back_populates="service", cascade="all, delete-orphan")

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="SEV-2", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    service: Mapped["Service"] = relationship("Service", back_populates="incidents")
    events: Mapped[list["IncidentEvent"]] = relationship("IncidentEvent", back_populates="incident", cascade="all, delete-orphan")
    hypotheses: Mapped[list["Hypothesis"]] = relationship("Hypothesis", back_populates="incident", cascade="all, delete-orphan")
    remediations: Mapped[list["RemediationAction"]] = relationship("RemediationAction", back_populates="incident", cascade="all, delete-orphan")
    agent_runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="incident", cascade="all, delete-orphan")

class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="events")

class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    template: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    labels: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_metrics_service_name_time", Metric.service, Metric.metric_name, Metric.timestamp)
Index("ix_logs_service_time", Log.service, Log.timestamp)

class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    span_id: Mapped[str] = mapped_column(String(100), nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OK", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="hypotheses")

class RemediationAction(Base):
    __tablename__ = "remediation_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    execution_status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED", nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="remediations")

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="SUCCEEDED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="agent_runs")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")

class DeploymentEvent(Base):
    __tablename__ = "deployment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="SUCCESS", nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
