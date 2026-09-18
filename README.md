# MultiModal-SRE — Autonomous AI-Powered SRE Operations Platform

MultiModal-SRE is an enterprise-grade autonomous Site Reliability Engineering platform that continuously analyzes multimodal telemetry (logs, time-series metrics, distributed traces, and deployment diffs), identifies statistical anomalies using Isolation Forest, orchestrates deep incident investigations using an agentic LangGraph workflow, grounds root cause analysis in hybrid RAG operational runbooks, and proposes safe, human-approved remediation with simulated execution and post-incident verification.

```
+---------------------------------------------------------------------------------------------------+
|                                      MULTIMODAL TELEMETRY                                         |
|  [Logs (Drain3/Regex)]  |  [Metrics (Prometheus)]  |  [Traces (OpenTelemetry)]  |  [Deployments]  |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
                                   [Isolation Forest Anomaly Model]
                                                  │
                                                  ▼
                                      [Incident Trigger & Queue]
                                                  │
                                                  ▼
                                   [LangGraph Investigation Agent]
                   ┌──────────────────────────────┼──────────────────────────────┐
                   ▼                              ▼                              ▼
          [Evidence Collector]        [Multimodal Timeline]             [Hybrid RAG Engine]
        (Logs/Metrics/Traces)       (Chronological Alignment)        (Qdrant Vector + BM25)
                   └──────────────────────────────┬──────────────────────────────┘
                                                  │
                                                  ▼
                                  [Evidence-Grounded Root Cause]
                                (Confidence + Facts vs Hypotheses)
                                                  │
                                                  ▼
                                     [Human-in-the-Loop Approval]
                                                  │
                                                  ▼
                                 [Safe Remediation & Simulation]
                               (Rollback / Replicas / DB Flush)
                                                  │
                                                  ▼
                                 [Post-Remediation Verification]
                               (Health Probes & Telemetry SLA)
```

---

## 🌟 Key Capabilities

1. **Multimodal Telemetry Correlation**: Correlates across heterogeneous signals (PostgreSQL connection pool logs, HTTP 5xx rates, P95/P99 latency spikes, distributed trace spans, and git deployment commits).
2. **Isolation Forest Anomaly Detection**: Ingests metrics with dynamic feature extraction (rate of change, rolling deviations) and statistical fallback for rapid anomaly detection without false-positive flooding.
3. **Pluggable Multi-Tier AI Reasoning Engine**:
   - **Deterministic Evidence Reasoner**: Zero-hallucination, evidence-grounded rule reasoner that parses empirical telemetry without static fake answers.
   - **Ollama Provider**: Local LLM inference (e.g. `qwen2.5-coder:7b`, `llama3.1`).
   - **OpenAI Compatible Provider**: Cloud LLMs (e.g. `gpt-4o-mini`, `gpt-4o`).
4. **Hybrid RAG Knowledge Retrieval**: Combines Qdrant dense vector cosine similarity with Okapi BM25 keyword matching via Reciprocal Rank Fusion (RRF) across 11+ curated SRE runbooks.
5. **Structured Pydantic SRE Schemas**: Returns validated root causes, confidence scores, rejected alternative hypotheses, primary citations, and quantitative verification criteria.
6. **Safety First & Human-in-the-Loop Governance**: Dangerous interventions require authorized human approval with simulation dry-runs and tamper-evident audit logs.
7. **Real-Time Next.js 14 Workspace**: Live WebSocket investigation progress streaming, interactive telemetry explorer, RAG search sandbox, and service topology monitors.

---

## 🏗️ Architectural Overview

| Layer | Technologies & Components |
|---|---|
| **Backend API** | FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Alembic migrations |
| **Worker & Queue** | Celery 5.4, Redis 7 (Async task dispatch & caching) |
| **Database** | PostgreSQL 16 (Relational models & audit trail) |
| **Vector DB / RAG** | Qdrant 1.12, Rank-BM25, N-gram Dense Embeddings, Markdown Runbooks |
| **Agent Framework** | LangGraph, StateGraph, Custom Step Notifiers |
| **ML / Detection** | Scikit-Learn Isolation Forest, Statistical Z-Score / IQR |
| **Observability** | Prometheus, Grafana, OpenTelemetry Collector |
| **Frontend** | Next.js 14, React 18, Custom Dark SRE Design System |
| **Infrastructure** | Docker Compose, Kubernetes manifests, Helm Charts, Terraform |

---

## 🚀 Quick Start (Local Docker Compose)

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ / Node.js 18+ (for local development)

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Start the Full Stack
```bash
docker compose build
docker compose up -d
docker compose ps
```

### 4. Access Services
- **SRE Web Platform**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Prometheus Metrics**: [http://localhost:9090](http://localhost:9090)
- **Grafana Dashboards**: [http://localhost:3001](http://localhost:3001) *(Login: `admin` / `admin`)*
- **Qdrant Vector Console**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## 🧪 Interactive End-to-End Demo Workflow

### Option A: From the Next.js UI
1. Open [http://localhost:3000](http://localhost:3000).
2. Click **"Quick Connect Demo Mode"** to authenticate as `admin@local`.
3. Click **"🔥 DB Pool Timeout (Payment API)"** to inject a realistic production failure.
4. Click **"Investigate →"** on the newly generated incident.
5. In the Incident Workspace, click **"⚡ Run AI Investigation"** to watch live streaming agent steps:
   - *Ingesting logs, metrics, traces, and deployments*
   - *Correlating multimodal timeline*
   - *Querying hybrid RAG for `postgres-connection-pool.md`*
   - *Synthesizing evidence-backed RCA (92% confidence)*
6. Switch to the **"🛡️ Safe Remediation & Approval"** tab.
7. Click **"✓ Approve & Simulate Remediation"** to execute simulated rollback to `v1.8.2` and verify service health recovery.

### Option B: From the Command Line
Run the automated scenario generator:
```bash
python scripts/generate_incidents.py --scenario database-timeout
```

---

## 📊 Evaluation & Benchmarking

Run the ground-truth benchmark suite against all 20 incident scenarios:
```bash
python scripts/run_evaluation.py
```

Expected benchmark metrics:
- **Retrieval Recall@1**: $\ge 90\%$
- **Retrieval Recall@3**: $100\%$
- **Root Cause Accuracy**: $\ge 95\%$
- **Mean Confidence**: $\ge 0.88$

---

## 🛡️ SRE Runbooks Catalog

The platform includes comprehensive operational runbooks indexed in `data/runbooks/`:
- `postgres-connection-pool.md` — PostgreSQL connection pool exhaustion & queue timeouts.
- `redis-connection-failure.md` — Redis latency, socket timeouts, and maxmemory pressure.
- `kubernetes-crashloop.md` — K8s CrashLoopBackOff & container OOMKilled (exit code 137).
- `cpu-saturation.md` — CPU CFS quota throttling and worker thread pool starvation.
- `memory-pressure-leak.md` — Heap memory exhaustion, garbage collection pauses, and leaks.
- `http-5xx-spikes.md` — HTTP 500/502/504 gateway timeout surges.
- `database-deadlocks.md` — Transaction lock contention and cyclic deadlocks (40P01).
- `deployment-rollback.md` — Safe zero-downtime rollback and regression mitigation.
- `service-dependency-failure.md` — Downstream cascading service dependency failures.
- `payment-api-database-timeout.md` — Payment API DB timeout diagnostic checklist.
- `payment-api-high-latency.md` — Payment API latency triage and resolution.

---

## 🔒 Security & Governance

- **RBAC**: Enforced role-based access control (`ADMIN`, `SRE_ENGINEER`, `VIEWER`).
- **Cryptographic Security**: Passwords hashed with `bcrypt`, JWT access tokens signed with HMAC-SHA256.
- **Audit Trails**: Every incident creation, agent investigation, human approval, and simulation execution writes immutable audit records in PostgreSQL.
- **Simulation Mode**: Automatic safety enforcement prevents destructive commands in production environments without explicit human sign-off.
