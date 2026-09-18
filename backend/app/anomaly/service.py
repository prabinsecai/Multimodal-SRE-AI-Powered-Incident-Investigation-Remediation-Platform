from datetime import datetime, timezone, timedelta
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.anomaly.detector import AnomalyDetector
from app.models.models import Metric, Incident, Service, IncidentEvent

async def detect_metric_anomaly(
    db: AsyncSession,
    service_name: str,
    metric_name: str,
    threshold: float = 0.65
) -> dict | None:
    """
    Evaluates incoming metric telemetry against historical window,
    computes real anomaly score, and triggers incident if threshold is breached.
    """
    stmt = (
        select(Metric)
        .where(Metric.service == service_name, Metric.metric_name == metric_name)
        .order_by(Metric.timestamp.desc())
        .limit(200)
    )
    rows = (await db.execute(stmt)).scalars().all()
    if len(rows) < 5:
        return {
            "anomaly_detected": False,
            "score": 0.0,
            "reason": "Insufficient historical points for baseline (< 5)",
            "incident_id": None
        }

    # Chronological order
    sorted_rows = list(reversed(rows))
    raw_values = np.array([x.value for x in sorted_rows], dtype=float)

    detector = AnomalyDetector(contamination=0.08)
    detector.fit(raw_values)
    scores = detector.score(raw_values)
    latest_score = float(scores[-1])

    if latest_score < threshold:
        return {
            "anomaly_detected": False,
            "score": round(latest_score, 4),
            "incident_id": None
        }

    # Find service
    svc_stmt = select(Service).where(Service.name == service_name)
    svc = (await db.execute(svc_stmt)).scalar_one_or_none()
    if not svc:
        svc = Service(name=service_name, environment="production", owner="sre-team")
        db.add(svc)
        await db.commit()
        await db.refresh(svc)

    # Check for existing open incident for this service within the last 15 minutes to avoid deduplication flooding
    fifteen_min_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
    existing_stmt = select(Incident).where(
        and_(
            Incident.service_id == svc.id,
            Incident.status.in_(["OPEN", "INVESTIGATING", "AWAITING_APPROVAL"]),
            Incident.detected_at >= fifteen_min_ago
        )
    )
    existing_inc = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing_inc:
        return {
            "anomaly_detected": True,
            "score": round(latest_score, 4),
            "incident_id": existing_inc.id,
            "deduplicated": True
        }

    # Determine severity based on actual anomaly score
    if latest_score >= 0.85:
        severity = "SEV-1"
    elif latest_score >= 0.75:
        severity = "SEV-2"
    else:
        severity = "SEV-3"

    title = f"Anomaly: {metric_name} spike on {service_name} (score: {latest_score:.2f})"
    now_utc = datetime.now(timezone.utc)
    inc = Incident(
        title=title,
        service_id=svc.id,
        severity=severity,
        status="OPEN",
        detected_at=now_utc,
        confidence=round(latest_score, 2)
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)

    # Add detection event
    event = IncidentEvent(
        incident_id=inc.id,
        event_type="anomaly_detected",
        source="isolation_forest",
        payload={
            "service": service_name,
            "metric_name": metric_name,
            "anomaly_score": round(latest_score, 4),
            "threshold": threshold,
            "latest_value": float(raw_values[-1])
        },
        timestamp=now_utc
    )
    db.add(event)
    await db.commit()

    return {
        "anomaly_detected": True,
        "score": round(latest_score, 4),
        "incident_id": inc.id,
        "severity": severity,
        "deduplicated": False
    }
