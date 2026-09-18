from app.rag.hybrid import HybridRetriever, load_runbooks

def test_hybrid_retriever_search():
    sample_docs = [
        {"name": "postgres-connection-pool.md", "title": "PostgreSQL Connection Pool", "text": "PostgreSQL connection pool exhaustion occurs when active connections reach limit, causing timeout errors and 504 gateway responses."},
        {"name": "redis-connection-failure.md", "title": "Redis Failure", "text": "Redis socket connection timeout and cache miss storms occur under high memory pressure or slow commands."},
        {"name": "kubernetes-crashloop.md", "title": "K8s CrashLoop", "text": "Kubernetes CrashLoopBackOff and OOMKilled exit code 137 container crashes due to memory limits."},
    ]

    retriever = HybridRetriever(docs=sample_docs)
    results = retriever.search("database connection pool timeout", k=2)

    assert len(results) > 0
    assert results[0]["name"] == "postgres-connection-pool.md"
    assert results[0]["score"] > 0.0

def test_load_runbooks():
    docs = load_runbooks()
    assert len(docs) >= 3
    doc_names = [d["name"] for d in docs]
    assert "postgres-connection-pool.md" in doc_names
