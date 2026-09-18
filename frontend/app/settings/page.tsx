'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function SettingsPage() {
  const [health, setHealth] = useState<any>(null);
  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => {
    fetch(`${API}/api/v1/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setHealth(d))
      .catch((e) => console.error(e));
  }, []);

  return (
    <div style={{ maxWidth: '800px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1>Platform Configuration & AI Settings</h1>
        <p className="muted">Configure multimodal ingestion sensitivity, AI reasoning models, and execution modes.</p>
      </div>

      <div className="card" style={{ marginBottom: '20px' }}>
        <h3>AI Investigation Engine</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '14px' }}>
          <div>
            <label className="dim" style={{ display: 'block', marginBottom: '4px' }}>Active Model Provider</label>
            <input
              type="text"
              value={health?.model_provider || 'Deterministic (Evidence-Based Rule Engine)'}
              disabled
              style={{ opacity: 0.8 }}
            />
          </div>

          <div>
            <label className="dim" style={{ display: 'block', marginBottom: '4px' }}>Model Name / Checkpoint</label>
            <input
              type="text"
              value={health?.model_name || 'qwen2.5-coder:7b'}
              disabled
              style={{ opacity: 0.8 }}
            />
          </div>

          <div>
            <label className="dim" style={{ display: 'block', marginBottom: '4px' }}>Execution Mode</label>
            <span className="badge badge-resolved">SIMULATION (Mock Kubernetes Provider)</span>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Isolation Forest Anomaly Sensitivity</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '14px' }}>
          <div>
            <label className="dim" style={{ display: 'block', marginBottom: '4px' }}>Anomaly Threshold Score (0.65 Default)</label>
            <input type="range" min="0.5" max="0.9" step="0.05" defaultValue="0.65" disabled />
          </div>

          <div className="card-subtle">
            <span className="muted" style={{ fontSize: '0.85rem' }}>
              Anomaly scores breaching this threshold trigger automated incident creation in the queue.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
