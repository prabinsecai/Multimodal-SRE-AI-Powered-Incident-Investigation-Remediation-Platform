import sys
from pathlib import Path

def validate():
    root = Path(__file__).resolve().parents[1]
    required_files = [
        "README.md",
        "docker-compose.yml",
        "backend/app/main.py",
        "backend/app/agents/workflow.py",
        "backend/app/agents/llm.py",
        "backend/app/rag/hybrid.py",
        "backend/app/anomaly/detector.py",
        "backend/app/anomaly/service.py",
        "backend/alembic/versions/0001_initial.py",
        "frontend/package.json",
        "frontend/app/layout.tsx",
        "frontend/app/page.tsx",
        "frontend/app/incidents/page.tsx",
        "frontend/app/incidents/[id]/page.tsx",
        "frontend/app/knowledge/page.tsx",
        "frontend/app/services/page.tsx",
        "frontend/app/observability/page.tsx",
        "frontend/app/audit/page.tsx",
        "frontend/app/settings/page.tsx",
        "observability/prometheus/prometheus.yml",
        "observability/grafana/provisioning/datasources/prometheus.yaml",
        "observability/grafana/dashboards/sre-overview.json",
        "data/runbooks/postgres-connection-pool.md",
        "data/runbooks/redis-connection-failure.md",
        "data/runbooks/kubernetes-crashloop.md",
    ]

    missing = [p for p in required_files if not (root / p).exists()]
    if missing:
        print(f"Validation FAILED: Missing {len(missing)} required files:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)

    print(f"Validation PASSED: All {len(required_files)} core system files verified.")

if __name__ == "__main__":
    validate()
