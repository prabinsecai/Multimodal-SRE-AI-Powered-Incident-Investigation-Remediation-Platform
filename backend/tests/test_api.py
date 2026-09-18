import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.core.db import Base, get_db
from app.core.security import create_token
from app.models.models import Service

# Setup test in-memory SQLite database
TEST_DB_URL = "sqlite+aiosqlite:///./test_api.db"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

async def override_get_db():
    async with TestSession() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def setup_test_database():
    import asyncio
    async def init_models():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with TestSession() as db:
            s = Service(name="payment-api", environment="test", owner="test-team", status="healthy")
            db.add(s)
            await db.commit()
    asyncio.run(init_models())
    yield
    async def cleanup_models():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()
        try:
            if os.path.exists("./test_api.db"):
                os.remove("./test_api.db")
        except Exception:
            pass
    asyncio.run(cleanup_models())

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_prometheus_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"sre_http_requests_total" in response.content

def test_knowledge_search():
    token = create_token("1", "ADMIN")
    response = client.post(
        "/api/v1/knowledge/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "database timeout", "limit": 3}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_telemetry_ingest_and_query():
    token = create_token("1", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    # Ingest log
    log_resp = client.post(
        "/api/v1/logs/ingest",
        headers=headers,
        json={
            "service": "payment-api",
            "timestamp": "2026-09-01T10:00:00Z",
            "level": "ERROR",
            "message": "database timeout acquiring connection from pool"
        }
    )
    assert log_resp.status_code == 200

    # Ingest metric
    metric_resp = client.post(
        "/api/v1/metrics/ingest",
        headers=headers,
        json={
            "service": "payment-api",
            "metric_name": "http_5xx_rate",
            "value": 0.12,
            "timestamp": "2026-09-01T10:00:00Z"
        }
    )
    assert metric_resp.status_code == 200

    # Query logs
    get_logs = client.get("/api/v1/logs?service=payment-api", headers=headers)
    assert get_logs.status_code == 200
    assert len(get_logs.json()) > 0
