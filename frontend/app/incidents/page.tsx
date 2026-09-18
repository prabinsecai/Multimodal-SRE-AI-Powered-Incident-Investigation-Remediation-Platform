'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newServiceId, setNewServiceId] = useState<number | ''>('');
  const [newSeverity, setNewSeverity] = useState('SEV-2');
  const [token, setToken] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  const loadIncidents = async () => {
    const t = localStorage.getItem('token');
    setToken(t);
    setErrorMsg('');
    try {
      const [incRes, svcRes] = await Promise.all([
        fetch(`${API}/api/v1/incidents`, { headers: t ? { Authorization: `Bearer ${t}` } : {} }),
        fetch(`${API}/api/v1/services`, { headers: t ? { Authorization: `Bearer ${t}` } : {} }),
      ]);
      if (incRes.ok) setIncidents(await incRes.json());
      else setErrorMsg('Failed to load incidents.');
      if (svcRes.ok) {
        const svcs = await svcRes.json();
        setServices(svcs);
        if (svcs.length > 0 && !newServiceId) setNewServiceId(svcs[0].id);
      } else {
        setErrorMsg((prev) => prev ? prev + ' Failed to load services.' : 'Failed to load services.');
      }
    } catch (e) {
      console.error(e);
      setErrorMsg('Network error occurred.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !newTitle || !newServiceId) return;

    setCreateLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch(`${API}/api/v1/incidents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: newTitle,
          service_id: Number(newServiceId),
          severity: newSeverity,
        }),
      });
      if (res.ok) {
        setShowModal(false);
        setNewTitle('');
        loadIncidents();
      } else {
        const data = await res.json();
        setErrorMsg(`Failed to create incident: ${data.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(err);
      setErrorMsg('Network error occurred while creating incident.');
    } finally {
      setCreateLoading(false);
    }
  };

  const filtered = incidents.filter((i) => {
    if (statusFilter && i.status !== statusFilter) return false;
    if (severityFilter && i.severity !== severityFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        i.title.toLowerCase().includes(q) ||
        (i.service_name && i.service_name.toLowerCase().includes(q)) ||
        String(i.id).includes(q) ||
        (i.root_cause && i.root_cause.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1>Production Incidents</h1>
          <p className="muted">Track, triage, and execute AI-guided root cause analysis across microservices.</p>
        </div>

        <button onClick={() => setShowModal(true)} className="btn btn-primary">
          + Trigger Incident
        </button>
      </div>

      {/* Filter Controls */}
      <div className="card" style={{ marginBottom: '20px', padding: '14px 20px' }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: 1, minWidth: '240px' }}>
            <input
              type="text"
              placeholder="Search by title, service, root cause, or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div style={{ width: '180px' }}>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="AWAITING_APPROVAL">AWAITING APPROVAL</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>

          <div style={{ width: '150px' }}>
            <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
              <option value="">All Severities</option>
              <option value="SEV-1">SEV-1 Critical</option>
              <option value="SEV-2">SEV-2 Major</option>
              <option value="SEV-3">SEV-3 Minor</option>
            </select>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="card-subtle" style={{ marginBottom: '20px', borderColor: '#ef4444', color: '#f87171' }}>
          ⚠️ {errorMsg}
        </div>
      )}

      {loading && (
        <div className="card-subtle" style={{ marginBottom: '20px', color: '#93c5fd' }}>
          Loading incidents...
        </div>
      )}

      {/* Incidents Table */}
      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Severity</th>
                <th>Service</th>
                <th>Title & Diagnostics</th>
                <th>Status</th>
                <th>Detected At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '32px' }} className="muted">
                    No incidents match your filter criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((inc) => (
                  <tr key={inc.id}>
                    <td className="dim">#{inc.id}</td>
                    <td>
                      <span className={`badge badge-${inc.severity.toLowerCase().replace('-', '')}`}>
                        {inc.severity}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{inc.service_name}</td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{inc.title}</div>
                      {inc.root_cause && (
                        <div className="muted" style={{ fontSize: '0.8rem', color: '#6ee7b7' }}>
                          ✓ RCA: {inc.root_cause} ({Math.round((inc.confidence || 0.85) * 100)}%)
                        </div>
                      )}
                    </td>
                    <td>
                      <span className={`badge badge-${inc.status.toLowerCase().replace('_', '')}`}>
                        {inc.status}
                      </span>
                    </td>
                    <td className="dim">
                      {inc.detected_at ? new Date(inc.detected_at).toLocaleTimeString() : 'Just now'}
                    </td>
                    <td>
                      <Link href={`/incidents/${inc.id}`} className="btn btn-outline btn-sm">
                        Inspect →
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Incident Creation Modal */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h2>Trigger New SRE Incident</h2>
            <p className="muted" style={{ marginBottom: '16px' }}>
              Register a production degradation to initiate automated LangGraph investigation.
            </p>

            <form onSubmit={handleCreateIncident} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label className="dim" style={{ display: 'block', marginBottom: '6px' }}>Target Microservice</label>
                <select
                  value={newServiceId}
                  onChange={(e) => setNewServiceId(Number(e.target.value))}
                  required
                >
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.environment})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="dim" style={{ display: 'block', marginBottom: '6px' }}>Severity Level</label>
                <select value={newSeverity} onChange={(e) => setNewSeverity(e.target.value)}>
                  <option value="SEV-1">SEV-1 (Critical outage / customer-facing failure)</option>
                  <option value="SEV-2">SEV-2 (Major performance degradation / error spikes)</option>
                  <option value="SEV-3">SEV-3 (Minor anomaly / non-critical service degraded)</option>
                </select>
              </div>

              <div>
                <label className="dim" style={{ display: 'block', marginBottom: '6px' }}>Incident Summary Title</label>
                <input
                  type="text"
                  placeholder="e.g., Payment API HTTP 504 gateway timeout surge"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" onClick={() => setShowModal(false)} className="btn btn-outline" disabled={createLoading}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={createLoading}>
                  {createLoading ? 'Creating...' : 'Create Incident'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
