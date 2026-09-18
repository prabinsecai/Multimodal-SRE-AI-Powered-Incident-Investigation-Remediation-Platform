# Investigation Agent Design Specification

## Workflow Graph
The MultiModal-SRE Investigation Agent is implemented as a cyclical/DAG state graph using LangGraph:

```
[Context Node] ──► [Telemetry Node] ──► [Timeline Node] ──► [Hybrid RAG Node] ──► [RCA Synthesis Node] ──► END
```

## Node Responsibilities
1. **Context Node (`context`)**:
   - Queries `services` and `incidents` tables.
   - Sets environment, owner team, base SLA targets.
   - Emits `context_loaded` step event.

2. **Telemetry Node (`telemetry`)**:
   - Queries `logs`, `metrics`, `traces`, and `deployment_events` for the target service within the incident window.
   - Extracts structured evidence signals.
   - Emits `telemetry_collected` step event.

3. **Timeline Node (`timeline`)**:
   - Normalizes all telemetry types into chronological `TimelineEntry` items.
   - Labels severity (critical / warning / info).
   - Emits `timeline_correlated` step event.

4. **Hybrid RAG Node (`rag`)**:
   - Synthesizes search query from error logs, metric names, and incident title.
   - Searches vector database and BM25 index for operational runbooks.
   - Emits `rag_completed` step event.

5. **RCA Synthesis Node (`rca`)**:
   - Invokes active AI engine (Ollama, OpenAI, or Deterministic Reasoner).
   - Validates JSON output strictly against Pydantic `StructuredInvestigationResult`.
   - Emits `rca_completed` step event.

## Core Prompt & SRE Grounding
The agent adheres to the Principal SRE Prompt rules:
- Strictly evidence-grounded reasoning without hallucinations.
- Multimodal correlation (comparing log timestamps against deployment events and metric spikes).
- Facts vs. Hypotheses separation.
- Explicit evaluation and rejection of competing alternative causes.
- Structured verification criteria.
