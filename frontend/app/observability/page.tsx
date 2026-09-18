'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ObservabilityPage() {
  const [activeTab, setActiveTab] = useState<'logs' | 'metrics' | 'traces' | 'deployments'>('logs');
  const [logs, setLogs] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any[]>([]);
  const [traces, setTraces] = useState<any[]>([]);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    try {
      const [lRes, mRes, tRes, dRes] = await Promise.all([
        fetch(`${API}/api/v1/logs?limit=50`, { headers }),
        fetch(`${API}/api/v1/metrics?limit=50`, { headers }),
        fetch(`${API}/api/v1/traces?limit=50`, { headers }),
        fetch(`${API}/api/v1/deployments?limit=50`, { headers }),
      ]);
      if (lRes.ok) setLogs(await lRes.json());
      if (mRes.ok) setMetrics(await mRes.json());
      if (tRes.ok) setTraces(await tRes.json());
      if (dRes.ok) setDeployments(await dRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1>Observability & Telemetry Explorer</h1>
          <p className="muted">Live streams of logs, time-series metrics, distributed traces, and deployment events.</p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <a href="http://localhost:3001" target="_blank" rel="noreferrer" className="btn btn-outline">
            📊 Grafana Dashboards ↗
          </a>
          <a href="http://localhost:9090" target="_blank" rel="noreferrer" className="btn btn-outline">
            📈 Prometheus Metrics ↗
          </a>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="tab-list">
        <button
          onClick={() => setActiveTab('logs')}
          className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
        >
          📜 Log Stream ({logs.length})
        </button>
        <button
          onClick={() => setActiveTab('metrics')}
          className={`tab-btn ${activeTab === 'metrics' ? 'active' : ''}`}
        >
          📈 Metrics Data ({metrics.length})
        </button>
        <button
          onClick={() => setActiveTab('traces')}
          className={`tab-btn ${activeTab === 'traces' ? 'active' : ''}`}
        >
          🔗 Distributed Traces ({traces.length})
        </button>
        <button
          onClick={() => setActiveTab('deployments')}
          className={`tab-btn ${activeTab === 'deployments' ? 'active' : ''}`}
        >
          🚀 Deployments ({deployments.length})
        </button>
      </div>

      {/* Content */}
      <div className="card">
        {activeTab === 'logs' && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Service</th>
                  <th>Level</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr><td colSpan={4} className="muted" style={{ textAlign: 'center', padding: '24px' }}>No logs recorded yet.</td></tr>
                ) : (
                  logs.map((l) => (
                    <tr key={l.id}>
                      <td className="dim">{new Date(l.timestamp).toLocaleTimeString()}</td>
                      <td style={{ fontWeight: 600 }}>{l.service}</td>
                      <td>
                        <span className={`badge ${l.level === 'ERROR' || l.level === 'CRITICAL' ? 'badge-sev1' : l.level === 'WARN' ? 'badge-sev2' : 'badge-sev3'}`}>
                          {l.level}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{l.message}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Service</th>
                  <th>Metric Name</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {metrics.length === 0 ? (
                  <tr><td colSpan={4} className="muted" style={{ textAlign: 'center', padding: '24px' }}>No metrics recorded yet.</td></tr>
                ) : (
                  metrics.map((m) => (
                    <tr key={m.id}>
                      <td className="dim">{new Date(m.timestamp).toLocaleTimeString()}</td>
                      <td style={{ fontWeight: 600 }}>{m.service}</td>
                      <td><code>{m.metric_name}</code></td>
                      <td style={{ fontWeight: 700, color: '#38bdf8' }}>{m.value}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'traces' && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Service</th>
                  <th>Trace ID</th>
                  <th>Span ID</th>
                  <th>Duration</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {traces.length === 0 ? (
                  <tr><td colSpan={6} className="muted" style={{ textAlign: 'center', padding: '24px' }}>No traces recorded yet.</td></tr>
                ) : (
                  traces.map((t) => (
                    <tr key={t.id}>
                      <td className="dim">{new Date(t.timestamp).toLocaleTimeString()}</td>
                      <td style={{ fontWeight: 600 }}>{t.service}</td>
                      <td><code>{t.trace_id}</code></td>
                      <td className="dim">{t.span_id}</td>
                      <td>{t.duration ? `${(t.duration * 1000).toFixed(0)}ms` : '0ms'}</td>
                      <td>
                        <span className={`badge ${t.status === 'ERROR' ? 'badge-sev1' : 'badge-resolved'}`}>
                          {t.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'deployments' && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Service</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Metadata</th>
                </tr>
              </thead>
              <tbody>
                {deployments.length === 0 ? (
                  <tr><td colSpan={5} className="muted" style={{ textAlign: 'center', padding: '24px' }}>No deployment events recorded yet.</td></tr>
                ) : (
                  deployments.map((d) => (
                    <tr key={d.id}>
                      <td className="dim">{new Date(d.timestamp).toLocaleTimeString()}</td>
                      <td style={{ fontWeight: 600 }}>{d.service}</td>
                      <td><span className="badge badge-sev3">{d.version}</span></td>
                      <td><span className="badge badge-resolved">{d.status}</span></td>
                      <td style={{ fontSize: '0.82rem', fontFamily: 'monospace', color: '#cbd5e1' }}>
                        {JSON.stringify(d.metadata_ || d.metadata || {})}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
