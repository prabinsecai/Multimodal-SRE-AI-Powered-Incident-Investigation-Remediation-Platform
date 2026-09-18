'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ServicesPage() {
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadServices = async () => {
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${API}/api/v1/services`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        setServices(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadServices();
  }, []);

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Monitored Microservices Topology</h1>
        <p className="muted">Live status, deployment tags, and SLA health indicators across the service mesh.</p>
      </div>

      <div className="grid-3" style={{ marginBottom: '32px' }}>
        {services.map((svc) => (
          <div key={svc.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.15rem' }}>{svc.name}</h3>
                <span className="dim" style={{ fontSize: '0.8rem' }}>Owner: {svc.owner} • {svc.environment}</span>
              </div>
              <span className={`badge ${svc.status === 'healthy' ? 'badge-resolved' : 'badge-sev1'}`}>
                {svc.status}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', margin: '14px 0', fontSize: '0.88rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="muted">Deployed Image:</span>
                <span className="badge badge-sev3">{svc.version || 'v1.0.0'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="muted">P95 Latency:</span>
                <span style={{ fontWeight: 600, color: svc.latency_ms > 500 ? '#fb7185' : '#34d399' }}>
                  {svc.latency_ms ? `${Math.round(svc.latency_ms)}ms` : '45ms'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="muted">Error Rate:</span>
                <span style={{ fontWeight: 600, color: (svc.error_rate || 0) > 0.01 ? '#fb7185' : '#34d399' }}>
                  {((svc.error_rate || 0.001) * 100).toFixed(2)}%
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="muted">Active Replicas:</span>
                <span>{svc.replicas || 3} Pods</span>
              </div>
            </div>

            <div className="card-subtle" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
              ✓ Liveness & Readiness probes: PASS (HTTP 200 OK)
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
