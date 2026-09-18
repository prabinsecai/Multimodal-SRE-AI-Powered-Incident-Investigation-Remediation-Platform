'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function KnowledgePage() {
  const [runbooks, setRunbooks] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedRunbook, setSelectedRunbook] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadRunbooks = async () => {
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${API}/api/v1/knowledge/runbooks`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        setRunbooks(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRunbooks();
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    setSearching(true);
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${API}/api/v1/knowledge/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ query, limit: 5 }),
      });
      if (res.ok) {
        setSearchResults(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>SRE Knowledge Base & Hybrid RAG</h1>
        <p className="muted">
          Curated runbooks indexed into Qdrant vector database and BM25 inverted index with Reciprocal Rank Fusion.
        </p>
      </div>

      {/* Hybrid Search Tester */}
      <div className="card" style={{ marginBottom: '24px', background: 'linear-gradient(180deg, #111726 0%, #0c111e 100%)' }}>
        <h3 style={{ marginBottom: '8px' }}>Test Hybrid Retrieval Engine (BM25 + Dense Vector Search)</h3>
        <p className="muted" style={{ fontSize: '0.88rem', marginBottom: '14px' }}>
          Enter telemetry error messages, symptoms, or diagnostic queries to test runbook grounding.
        </p>

        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '12px' }}>
          <input
            type="text"
            placeholder="e.g. database connection pool timeout, redis latency, crashloopbackoff oomkilled..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={searching} className="btn btn-primary">
            {searching ? 'Retrieving...' : '🔍 Search Runbooks'}
          </button>
        </form>

        {searchResults.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <div className="dim" style={{ marginBottom: '10px' }}>TOP RANKED RETRIEVAL RESULTS (RRF SCORED)</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {searchResults.map((hit, idx) => (
                <div key={idx} className="card-subtle" style={{ borderColor: '#3b82f6' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 700, color: '#38bdf8' }}>📄 {hit.name}</span>
                    <span className="badge badge-sev3">Relevance: {Math.round(hit.score * 100)}%</span>
                  </div>
                  <p className="muted" style={{ fontSize: '0.85rem', margin: 0, lineHeight: 1.5 }}>
                    {hit.snippet || hit.text?.slice(0, 250)}...
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Runbooks Catalog Grid */}
      <h2>Indexed SRE Runbooks Catalog ({runbooks.length})</h2>
      <div className="grid-3">
        {runbooks.map((doc, idx) => (
          <div key={idx} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.2rem' }}>📑</span>
                <h3 style={{ margin: 0, fontSize: '1rem', color: '#f1f5f9' }}>{doc.title || doc.name}</h3>
              </div>
              <p className="muted" style={{ fontSize: '0.82rem', lineHeight: 1.5, marginBottom: '12px' }}>
                {doc.snippet}...
              </p>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
              <span className="dim" style={{ fontSize: '0.75rem' }}>{doc.name}</span>
              <span className="badge badge-resolved" style={{ fontSize: '0.7rem' }}>INDEXED</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
