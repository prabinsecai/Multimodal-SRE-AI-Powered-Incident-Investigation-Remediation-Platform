# Hybrid RAG Engine Design

## Overview
MultiModal-SRE combines dense vector search with sparse BM25 keyword matching to retrieve diagnostic runbooks with high recall and precision.

```
Diagnostic Query (Telemetry Symptoms)
                 │
        ┌────────┴────────┐
        ▼                 ▼
[Qdrant Vector Search] [BM25 Inverted Index]
(Dense Cosine Similarity) (Sparse Lexical Match)
        │                 │
        └────────┬────────┘
                 ▼
     [Reciprocal Rank Fusion]
                 │
                 ▼
  [Top-K Ranked SRE Runbooks]
```

## Embedding Strategy
- **Dense Embeddings**: N-gram hashed feature projection into 128-dimensional unit vector space with deterministic fallbacks when offline.
- **Qdrant Storage**: Cosine distance vector indexing with metadata payloads (runbook name, title, text).
- **BM25 Scoring**: Okapi BM25 ranking across tokenized runbook texts.
- **Hybrid Fusion**: Weighted linear score combination ($0.6 \times \text{Dense} + 0.4 \times \text{BM25}$) ensuring exact symptom keywords and semantic concepts are both retrieved.
