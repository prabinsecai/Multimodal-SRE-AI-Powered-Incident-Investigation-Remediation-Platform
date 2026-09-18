import os
from pathlib import Path
import hashlib
import re
from typing import Any
from rank_bm25 import BM25Okapi
from app.core.config import settings

class HybridRetriever:
    """
    Hybrid SRE Knowledge Retriever combining BM25 Keyword Search
    and Qdrant Vector Similarity with Reciprocal Rank Fusion (RRF).
    """
    def __init__(self, docs: list[dict[str, Any]] | None = None):
        self.docs = docs or []
        self.dim = 128
        self.collection_name = "sre_runbooks"
        self.tokens = [self._tokenize(d["text"]) for d in self.docs]
        self.bm25 = BM25Okapi(self.tokens) if self.tokens and any(self.tokens) else None

        # Initialize Qdrant Client conditionally
        self.client = None
        if os.getenv("ENABLE_QDRANT", "false").lower() in ("true", "1", "yes"):
            try:
                from qdrant_client import QdrantClient
                self.client = QdrantClient(url=settings.qdrant_url, timeout=0.5)
                self._ensure_collection()
            except Exception:
                self.client = None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9_\-.:#]+", text.lower())

    def _embed(self, text: str) -> list[float]:
        """
        Deterministic dense embedding vector calculation.
        Computes n-gram hashed features normalized to unit sphere.
        """
        vec = [0.0] * self.dim
        tokens = self._tokenize(text)
        if not tokens:
            return vec

        # Unigrams and bigrams
        terms = list(tokens)
        for i in range(len(tokens) - 1):
            terms.append(f"{tokens[i]}_{tokens[i+1]}")

        for term in terms:
            h = int(hashlib.sha256(term.encode("utf-8")).hexdigest(), 16)
            for j in range(4):
                idx = (h + j * 9973) % self.dim
                weight = 1.0 + (0.5 if "_" in term else 0.0)
                vec[idx] += weight

        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [round(x / norm, 6) for x in vec]

    def _ensure_collection(self):
        if not self.client:
            return
        try:
            from qdrant_client.models import Distance, VectorParams, PointStruct
            collections = self.client.get_collections().collections
            existing_names = {c.name for c in collections}
            if self.collection_name not in existing_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
                )
            if self.docs:
                points = []
                for i, doc in enumerate(self.docs):
                    points.append(
                        PointStruct(
                            id=i + 1,
                            vector=self._embed(doc["text"]),
                            payload={
                                "name": doc["name"],
                                "text": doc["text"][:2000],
                                "title": doc.get("title", doc["name"]),
                            },
                        )
                    )
                self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception:
            pass

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """
        Hybrid search combining BM25 keyword score and dense vector cosine similarity.
        """
        if not self.docs:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            query_tokens = ["sre", "incident", "failure"]

        # 1. BM25 Scores
        bm25_scores = {}
        if self.bm25:
            scores = self.bm25.get_scores(query_tokens)
            max_b = max(scores, default=1.0) or 1.0
            for i, score in enumerate(scores):
                bm25_scores[i] = max(0.0, float(score) / max_b)
        else:
            for i in range(len(self.docs)):
                bm25_scores[i] = 0.0

        # 2. Vector Cosine Similarity
        q_vec = self._embed(query)
        dense_scores = {}
        qdrant_succeeded = False

        if self.client:
            try:
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=q_vec,
                    limit=min(len(self.docs), k * 2),
                )
                for hit in hits:
                    idx = int(hit.id) - 1
                    if 0 <= idx < len(self.docs):
                        dense_scores[idx] = max(0.0, float(hit.score))
                qdrant_succeeded = True
            except Exception:
                qdrant_succeeded = False

        if not qdrant_succeeded:
            # Local cosine similarity fallback
            for i, doc in enumerate(self.docs):
                doc_vec = self._embed(doc["text"])
                cos_sim = sum(a * b for a, b in zip(q_vec, doc_vec))
                dense_scores[i] = max(0.0, cos_sim)

        # 3. Hybrid Fusion (0.6 * Dense + 0.4 * BM25)
        combined = []
        for i, doc in enumerate(self.docs):
            d_score = dense_scores.get(i, 0.0)
            b_score = bm25_scores.get(i, 0.0)
            final_score = 0.6 * d_score + 0.4 * b_score
            combined.append((i, final_score))

        combined.sort(key=lambda x: x[1], reverse=True)
        top_k = combined[:k]

        results = []
        for i, score in top_k:
            doc = self.docs[i]
            # Extract relevant snippet
            text = doc["text"]
            lines = [line.strip() for line in text.split("\n") if line.strip() and not line.startswith("#")]
            snippet = " ".join(lines[:3]) if lines else text[:200]
            results.append({
                "name": doc["name"],
                "score": round(score, 4),
                "text": text,
                "snippet": snippet[:300]
            })

        return results

def load_runbooks(directory: str | None = None) -> list[dict[str, Any]]:
    """
    Loads all markdown runbooks from data/runbooks directory.
    """
    dir_path = directory or os.getenv("RUNBOOK_DIR")
    if not dir_path:
        candidates = [
            Path("/app/data/runbooks"),
            Path(__file__).resolve().parents[3] / "data" / "runbooks",
            Path("data/runbooks"),
            Path("../data/runbooks"),
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                dir_path = str(c)
                break

    if not dir_path or not Path(dir_path).exists():
        return []

    docs = []
    for p in Path(dir_path).glob("*.md"):
        try:
            content = p.read_text(encoding="utf-8")
            title = p.stem.replace("-", " ").title()
            match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if match:
                title = match.group(1).strip()
            docs.append({"name": p.name, "title": title, "text": content})
        except Exception:
            continue

    return sorted(docs, key=lambda x: x["name"])
