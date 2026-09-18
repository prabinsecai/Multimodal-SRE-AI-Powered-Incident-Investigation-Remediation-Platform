'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [token, setToken] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const loadData = async (authToken?: string) => {
    const t = authToken || localStorage.getItem('token');
    if (!t) {
      setLoading(false);
      return;
    }
    setToken(t);
    try {
      const [incRes, svcRes] = await Promise.all([
        fetch(`${API}/api/v1/incidents`, { headers: { Authorization: `Bearer ${t}` } }),
        fetch(`${API}/api/v1/services`, { headers: { Authorization: `Bearer ${t}` } }),
      ]);
      if (incRes.ok) setIncidents(await incRes.json());
      if (svcRes.ok) setServices(await svcRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const autoLogin = async () => {
    setStatusMsg('Signing in with demo admin credentials...');
    try {
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'admin@local', password: 'admin123' }),
      });
      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        setStatusMsg('Signed in successfully.');
        loadData(data.access_token);
      }
    } catch (e) {
      setStatusMsg('Failed to connect to backend API.');
    }
  };

  const triggerScenario = async (scenario: string) => {
    setScenarioLoading(true);
    setStatusMsg(`Injecting scenario: ${scenario}...`);
    try {
      const res = await fetch(`${API}/api/v1/demo/incidents/${scenario}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMsg(`Created incident #${data.incident_id} (${scenario})`);
        await loadData();
      } else {
        setStatusMsg(`Scenario failed: ${data.detail || 'Error'}`);
      }
    } catch (e) {
      setStatusMsg('Error triggering demo scenario.');
    } finally {
      setScenarioLoading(false);
    }
  };

  const openCount = incidents.filter((i) => i.status !== 'RESOLVED').length;
  const criticalCount = incidents.filter((i) => i.severity === 'SEV-1' && i.status !== 'RESOLVED').length;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1>Autonomous SRE Control Center</h1>
          <p className="muted">
            Continuous multimodal telemetry analysis, automated LangGraph investigation, and safe remediation.
          </p>
        </div>

        {!token && (
          <button onClick={autoLogin} className="btn btn-primary">
            Quick Connect Demo Mode
          </button>
        )}
      </div>

      {statusMsg && (
        <div className="card-subtle" style={{ marginBottom: '20px', borderColor: '#3b82f6', color: '#93c5fd' }}>
          ℹ️ {statusMsg}
        </div>
      )}

      {/* Overview Stat Cards */}
      <div className="grid-4" style={{ marginBottom: '24px' }}>
        <div className="card">
          <div className="dim">ACTIVE INCIDENTS</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: openCount > 0 ? '#fb7185' : '#34d399', margin: '4px 0' }}>
            {openCount}
          </div>
          <div className="muted">{criticalCount} Critical (SEV-1) requiring attention</div>
        </div>

        <div className="card">
          <div className="dim">MONITORED SERVICES</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#38bdf8', margin: '4px 0' }}>
            {services.length || 5}
          </div>
          <div className="muted">Payment, Order, Auth, Worker, Inventory</div>
        </div>

        <div className="card">
          <div className="dim">AI REASONING ENGINE</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#a855f7', margin: '8px 0' }}>
            Multi-tier SRE Agent
          </div>
          <div className="muted">LangGraph • Hybrid RAG • Isolation Forest</div>
        </div>

        <div className="card">
          <div className="dim">SAFETY & GOVERNANCE</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', margin: '8px 0' }}>
            Simulation & Approval
          </div>
          <div className="muted">Human-in-the-loop remediation</div>
        </div>
      </div>

      {/* Demo Scenario Launchers */}
      <div className="card" style={{ marginBottom: '28px', background: 'linear-gradient(180deg, #111726 0%, #0d1322 100%)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div>
            <h3>Deterministic Demo Scenario Generators</h3>
            <p className="muted" style={{ margin: 0 }}>
              Simulate realistic production anomalies with correlated logs, metrics, traces, and deployment diffs.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button
            disabled={!token || scenarioLoading}
            onClick={() => triggerScenario('database-timeout')}
            className="btn btn-primary"
          >
            🔥 DB Pool Timeout (Payment API)
          </button>

          <button
            disabled={!token || scenarioLoading}
            onClick={() => triggerScenario('redis-failure')}
            className="btn btn-accent"
          >
            ⚡ Redis Socket Timeout (Order API)
          </button>

          <button
            disabled={!token || scenarioLoading}
            onClick={() => triggerScenario('k8s-crashloop')}
            className="btn btn-danger"
          >
            💥 K8s OOMKilled CrashLoop (Auth API)
          </button>
        </div>
      </div>

      <div className="grid-2">
        {/* Incident Queue */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3>Recent Incidents Queue</h3>
            <Link href="/incidents" className="dim" style={{ textDecoration: 'underline' }}>
              View All
            </Link>
          </div>

          {incidents.length === 0 ? (
            <p className="muted">No incidents recorded yet. Launch a demo scenario above to test.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {incidents.slice(0, 5).map((inc) => (
                <div key={inc.id} className="card-subtle" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span className={`badge badge-${inc.severity.toLowerCase().replace('-', '')}`}>
                        {inc.severity}
                      </span>
                      <span className={`badge badge-${inc.status.toLowerCase().replace('_', '')}`}>
                        {inc.status}
                      </span>
                      <span className="dim">#{inc.id}</span>
                      <span style={{ fontWeight: 600 }}>{inc.service_name}</span>
                    </div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 500 }}>{inc.title}</div>
                    {inc.root_cause && (
                      <div className="muted" style={{ fontSize: '0.8rem', marginTop: '2px', color: '#6ee7b7' }}>
                        ✓ Root Cause: {inc.root_cause} ({Math.round((inc.confidence || 0.85) * 100)}%)
                      </div>
                    )}
                  </div>

                  <Link href={`/incidents/${inc.id}`} className="btn btn-outline btn-sm">
                    Investigate →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Monitored Services */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3>Monitored Microservices</h3>
            <Link href="/services" className="dim" style={{ textDecoration: 'underline' }}>
              Topology
            </Link>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Version</th>
                  <th>Latency</th>
                  <th>Error Rate</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc) => (
                  <tr key={svc.id}>
                    <td style={{ fontWeight: 600 }}>{svc.name}</td>
                    <td><span className="badge badge-sev3">{svc.version || 'v1.0.0'}</span></td>
                    <td>{svc.latency_ms ? `${Math.round(svc.latency_ms)}ms` : '45ms'}</td>
                    <td>{((svc.error_rate || 0.001) * 100).toFixed(2)}%</td>
                    <td>
                      <span className={`badge ${svc.status === 'healthy' ? 'badge-resolved' : 'badge-sev1'}`}>
                        {svc.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
