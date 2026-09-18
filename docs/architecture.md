# MultiModal-SRE System Architecture

## Overview
MultiModal-SRE is an autonomous SRE operations platform that unifies multimodal telemetry processing, statistical anomaly detection, agentic incident investigation, hybrid vector-keyword retrieval, and safe remediation execution.

```
                               ┌─────────────────────────┐
                               │   Telemetry Ingestion   │
                               │  (Logs, Metrics, Traces)│
                               └───────────┬─────────────┘
                                           │
                                           ▼
                               ┌─────────────────────────┐
                               │ Isolation Forest Model  │
                               │   Anomaly Detection     │
                               └───────────┬─────────────┘
                                           │
                                           ▼
                               ┌─────────────────────────┐
                               │  Incident Orchestration │
                               │     (FastAPI Core)      │
                               └───────────┬─────────────┘
                                           │
                                           ▼
                               ┌─────────────────────────┐
                               │   LangGraph Agentic     │
                               │      Workflow           │
                               └─────┬───────────────┬───┘
                                     │               │
                                     ▼               ▼
                       ┌───────────────────┐   ┌───────────────────┐
                       │ Hybrid RAG Engine │   │ Multi-tier AI     │
                       │ (Qdrant + BM25)   │   │ Reasoner/LLMs     │
                       └───────────────────┘   └───────────────────┘
                                           │
                                           ▼
                               ┌─────────────────────────┐
                               │ Root Cause Analysis &   │
                               │ Verification Plan (JSON)│
                               └───────────┬─────────────┘
                                           │
                                           ▼
                               ┌─────────────────────────┐
                               │ Human Approval Gate &   │
                               │ Remediation Simulator   │
                               └─────────────────────────┘
```

## Core Architectural Modules

### 1. Ingestion & Preprocessing
- **Log Stream Mining**: Ingests structured and unstructured log lines, extracting message patterns and template hashes.
- **Metric Time-Series**: Ingests high-frequency telemetry (error rates, latency percentiles, CPU/memory saturation, connection pool utilization).
- **Trace Spans**: Ingests OpenTelemetry-compatible traces and pinpoints latency bottlenecks and error flags.
- **Deployment Tracker**: Ingests release events with commit SHAs, author metadata, and diff summaries.

### 2. Anomaly Detection
- Multivariate feature extraction (rate of change, rolling standard deviations).
- Scikit-Learn `IsolationForest` scoring ($0.0 - 1.0$).
- Automatic statistical Z-score / IQR fallback for sparse cold-start baselines.
- Deduplication filter to prevent alert storms.

### 3. Agentic RCA (LangGraph)
- **Context Loading**: Fetches service environment and SLA metadata.
- **Telemetry Aggregation**: Pulls logs, metrics, traces, and deployment events within the incident timeframe.
- **Multimodal Timeline Correlation**: Aligns heterogeneous signals into a unified chronological sequence.
- **Hybrid RAG Retrieval**: Fetches grounded operational runbooks using combined BM25 keyword matching and dense vector similarity.
- **Reasoning & Synthesis**: Evaluates competing hypotheses, calculates calibrated confidence, and proposes minimal-risk remediation.

### 4. Safety & Governance
- Role-Based Access Control (RBAC).
- Human-in-the-loop approval gate.
- Remediation simulation mode (`rollback_deployment`, `scale_replicas`, `flush_connections`).
- Tamper-evident PostgreSQL audit trail.
