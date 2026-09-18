'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }
    fetch(`${API}/api/v1/audit`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setLogs(d))
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Security & Governance Audit Trail</h1>
        <p className="muted">Immutable log of all human approvals, automated agent runs, and remediation interventions.</p>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>User / Subject</th>
                <th>Action</th>
                <th>Resource Type</th>
                <th>Resource ID</th>
                <th>Metadata</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '32px' }} className="muted">
                    No audit records found. Sign in as Admin to view audit history.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id}>
                    <td className="dim">{new Date(log.timestamp).toLocaleString()}</td>
                    <td>{log.user_id ? `User #${log.user_id}` : 'System Agent'}</td>
                    <td><span className="badge badge-sev3">{log.action}</span></td>
                    <td style={{ fontWeight: 600 }}>{log.resource_type}</td>
                    <td><code>{log.resource_id}</code></td>
                    <td style={{ fontSize: '0.8rem', fontFamily: 'monospace', color: '#cbd5e1' }}>
                      {JSON.stringify(log.metadata_ || log.metadata || {})}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
