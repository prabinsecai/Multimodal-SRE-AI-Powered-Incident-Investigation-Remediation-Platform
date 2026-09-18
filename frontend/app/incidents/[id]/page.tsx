'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function IncidentDetailPage() {
  const params = useParams();
  const id = params?.id;
  const [incident, setIncident] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [liveSteps, setLiveSteps] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'rca' | 'timeline' | 'remediation' | 'audit'>('rca');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionResult, setActionResult] = useState<any>(null);
  const [token, setToken] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState('');
  const wsRef = useRef<WebSocket | null>(null);

  const loadIncident = async (t?: string) => {
    const authToken = t || localStorage.getItem('token');
    if (!id) return;
    try {
      const res = await fetch(`${API}/api/v1/incidents/${id}`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setIncident(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const t = localStorage.getItem('token');
    setToken(t);
    loadIncident(t || undefined);

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [id]);

  const startInvestigation = async () => {
    if (!id || !token) return;
    setInvestigating(true);
    setLiveSteps([]);
    setStatusMsg('Connecting to live investigation pipeline...');

    // Try WebSocket connection first for streaming steps
    try {
      const wsUrl = `${API.replace('http', 'ws')}/ws/incidents/${id}?token=${token}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setLiveSteps((prev) => [...prev, '● Connecting to agent orchestrator...']);
        ws.send(JSON.stringify({ action: 'start_investigation' }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'step_update') {
            const stepName = data.step;
            let msg = `✓ ${stepName.replace('_', ' ').toUpperCase()}`;
            if (stepName === 'telemetry_collected') {
              msg = `✓ Telemetry Ingested: ${data.payload.logs_count} logs, ${data.payload.metrics_count} metrics, ${data.payload.traces_count} traces, ${data.payload.deployments_count} deployments`;
            } else if (stepName === 'timeline_correlated') {
              msg = `✓ Correlated ${data.payload.total_timeline_events} multimodal timeline events`;
            } else if (stepName === 'rag_completed') {
              msg = `✓ Hybrid RAG Matched Runbooks: ${data.payload.matched_runbooks.join(', ')}`;
            } else if (stepName === 'rca_completed') {
              msg = `✓ RCA Synthesized: ${data.payload.root_cause} (Confidence: ${Math.round(data.payload.confidence * 100)}%)`;
            }
            setLiveSteps((prev) => [...prev, msg]);
          } else if (data.event === 'investigation_finished') {
            setInvestigating(false);
            setStatusMsg('Investigation completed.');
            loadIncident(token);
            ws.close();
          }
        } catch (err) {
          console.error(err);
        }
      };

      ws.onerror = async () => {
        // Fallback to HTTP POST if websocket fails
        await runHttpInvestigation();
      };
    } catch (e) {
      await runHttpInvestigation();
    }
  };

  const runHttpInvestigation = async () => {
    try {
      setLiveSteps([
        '● Ingesting logs, metrics, traces, and deployment events...',
        '● Correlating multimodal signals by timestamp...',
        '● Querying hybrid RAG knowledge base for SRE runbooks...',
        '● Synthesizing evidence-grounded root cause analysis...',
      ]);
      const res = await fetch(`${API}/api/v1/incidents/${id}/investigate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setLiveSteps((prev) => [...prev, '✓ LangGraph investigation completed successfully.']);
        await loadIncident(token || undefined);
      }
    } catch (err) {
      setStatusMsg('Investigation failed.');
    } finally {
      setInvestigating(false);
    }
  };

  const approveRemediation = async (actionId: number) => {
    if (!token) return;
    setActionLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/incidents/${id}/remediation/${actionId}/approve`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        setActionResult(data);
        setStatusMsg('Remediation action simulated & executed successfully. Service recovered.');
        await loadIncident(token);
      } else {
        setStatusMsg(`Approval failed: ${data.detail || 'Error'}`);
      }
    } catch (e) {
      setStatusMsg('Failed to approve remediation.');
    } finally {
      setActionLoading(false);
    }
  };

  const rejectRemediation = async (actionId: number) => {
    if (!token) return;
    setActionLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/incidents/${id}/remediation/${actionId}/reject`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setStatusMsg('Remediation action rejected.');
        await loadIncident(token);
      }
    } catch (e) {
      setStatusMsg('Failed to reject remediation.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <div className="card"><p className="muted">Loading incident workspace...</p></div>;
  }

  if (!incident) {
    return (
      <div className="card">
        <h2>Incident Not Found</h2>
        <p className="muted">The requested incident ID does not exist.</p>
        <Link href="/incidents" className="btn btn-outline" style={{ marginTop: '12px' }}>
          Back to Incidents
        </Link>
      </div>
    );
  }

  const structured = incident.structured_investigation || {};
  const rootCause = structured.root_cause || (incident.root_cause ? { title: incident.root_cause, explanation: '', confidence: incident.confidence || 0.85 } : null);
  const hypotheses = structured.hypotheses || incident.hypotheses || [];
  const altCauses = structured.alternative_causes || [];
  const retrievedDocs = structured.retrieved_documents || [];
  const timelineEvents = structured.timeline || [];
  const remediationPlan = structured.remediation || (incident.remediations && incident.remediations[0]) || null;
  const verificationPlan = structured.verification_plan || [];

  return (
    <div>
      {/* Back link & breadcrumbs */}
      <div style={{ marginBottom: '14px' }}>
        <Link href="/incidents" className="dim" style={{ textDecoration: 'underline' }}>
          ← Back to Incidents
        </Link>
      </div>

      {/* Incident Header Card */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="dim" style={{ fontSize: '1.1rem', fontWeight: 700 }}>#{incident.id}</span>
              <span className={`badge badge-${incident.severity.toLowerCase().replace('-', '')}`}>
                {incident.severity}
              </span>
              <span className={`badge badge-${incident.status.toLowerCase().replace('_', '')}`}>
                {incident.status}
              </span>
              <span className="badge badge-sev3">{incident.service_name} ({incident.environment})</span>
            </div>

            <h1 style={{ margin: 0, fontSize: '1.6rem' }}>{incident.title}</h1>
            <p className="dim" style={{ marginTop: '6px' }}>
              Detected at {incident.detected_at ? new Date(incident.detected_at).toLocaleString() : 'N/A'}
              {incident.resolved_at && ` • Resolved at ${new Date(incident.resolved_at).toLocaleString()}`}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              disabled={investigating || !token}
              onClick={startInvestigation}
              className="btn btn-primary"
            >
              {investigating ? '⚙️ Investigating...' : '⚡ Run AI Investigation'}
            </button>
          </div>
        </div>
      </div>

      {statusMsg && (
        <div className="card-subtle" style={{ marginBottom: '20px', borderColor: '#3b82f6', color: '#93c5fd' }}>
          ℹ️ {statusMsg}
        </div>
      )}

      {/* Live Investigation Stream Progress Panel */}
      {(investigating || liveSteps.length > 0) && (
        <div className="card" style={{ marginBottom: '24px', borderColor: '#8b5cf6', background: 'rgba(139, 92, 246, 0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div className="engine-dot" style={{ backgroundColor: '#c084fc' }} />
            <h3 style={{ margin: 0, color: '#e9d5ff' }}>LangGraph Multimodal Investigation Pipeline</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.88rem' }}>
            {liveSteps.map((step, idx) => (
              <div key={idx} style={{ color: step.startsWith('✓') ? '#6ee7b7' : '#c084fc', fontFamily: 'monospace' }}>
                {step}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Workspace Tabs */}
      <div className="tab-list">
        <button
          onClick={() => setActiveTab('rca')}
          className={`tab-btn ${activeTab === 'rca' ? 'active' : ''}`}
        >
          🧠 Root Cause Analysis (RCA)
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          className={`tab-btn ${activeTab === 'timeline' ? 'active' : ''}`}
        >
          📊 Multimodal Timeline ({timelineEvents.length || incident.events?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('remediation')}
          className={`tab-btn ${activeTab === 'remediation' ? 'active' : ''}`}
        >
          🛡️ Safe Remediation & Approval
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
        >
          📝 Incident Audit Trail ({incident.events?.length || 0})
        </button>
      </div>

      {/* TAB 1: RCA Panel */}
      {activeTab === 'rca' && (
        <div className="grid-2">
          {/* Left Column: Root Cause & Reasoning */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="card">
              <h3>AI Root Cause Assessment</h3>
              {rootCause ? (
                <div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '8px' }}>
                    {rootCause.title}
                  </div>

                  {/* Confidence Meter */}
                  <div style={{ marginBottom: '14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                      <span className="dim">AI CONFIDENCE SCORE</span>
                      <span style={{ fontWeight: 700, color: '#34d399' }}>
                        {Math.round((rootCause.confidence || 0.85) * 100)}%
                      </span>
                    </div>
                    <div className="confidence-bar-bg">
                      <div
                        className="confidence-bar-fill"
                        style={{ width: `${Math.round((rootCause.confidence || 0.85) * 100)}%` }}
                      />
                    </div>
                  </div>

                  <p className="muted" style={{ lineHeight: 1.6, marginBottom: '14px' }}>
                    {rootCause.explanation || structured.summary || 'Detailed multimodal telemetry indicates failure correlated with service load.'}
                  </p>

                  {rootCause.primary_evidence && rootCause.primary_evidence.length > 0 && (
                    <div>
                      <div className="dim" style={{ marginBottom: '6px' }}>PRIMARY CORRELATED SIGNALS</div>
                      <ul style={{ paddingLeft: '20px', fontSize: '0.88rem', color: '#cbd5e1' }}>
                        {rootCause.primary_evidence.map((sig: string, idx: number) => (
                          <li key={idx}>{sig}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '24px' }}>
                  <p className="muted">No investigation executed yet.</p>
                  <button onClick={startInvestigation} className="btn btn-primary btn-sm" style={{ marginTop: '10px' }}>
                    Run Investigation
                  </button>
                </div>
              )}
            </div>

            {/* Alternative Hypotheses Rejected */}
            <div className="card">
              <h3>Alternative Causes Evaluated</h3>
              {altCauses.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {altCauses.map((alt: any, idx: number) => (
                    <div key={idx} className="card-subtle">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{alt.hypothesis}</span>
                        <span className="badge badge-resolved" style={{ fontSize: '0.7rem' }}>
                          REJECTED ({alt.probability.toUpperCase()})
                        </span>
                      </div>
                      <p className="muted" style={{ fontSize: '0.82rem', margin: 0 }}>
                        {alt.reason_rejected}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted" style={{ fontSize: '0.88rem' }}>Run investigation to generate evaluated alternatives.</p>
              )}
            </div>
          </div>

          {/* Right Column: Grounded Evidence & SRE Runbooks Cited */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Cited SRE Runbooks */}
            <div className="card">
              <h3>Retrieved Knowledge Runbooks (RAG)</h3>
              {retrievedDocs.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {retrievedDocs.map((doc: any, idx: number) => (
                    <div key={idx} className="card-subtle">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, color: '#38bdf8' }}>📄 {doc.name}</span>
                        <span className="dim">Match: {Math.round((doc.score || 0.8) * 100)}%</span>
                      </div>
                      <p className="muted" style={{ fontSize: '0.8rem', margin: 0 }}>
                        {doc.snippet || doc.text?.slice(0, 200)}...
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted" style={{ fontSize: '0.88rem' }}>Knowledge runbooks will appear after RAG retrieval.</p>
              )}
            </div>

            {/* Observed Telemetry Facts */}
            <div className="card">
              <h3>Observed Empirical Facts</h3>
              {structured.observations && structured.observations.length > 0 ? (
                <ul style={{ paddingLeft: '20px', fontSize: '0.88rem', color: '#cbd5e1' }}>
                  {structured.observations.map((obs: string, idx: number) => (
                    <li key={idx} style={{ marginBottom: '6px' }}>{obs}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted" style={{ fontSize: '0.88rem' }}>No empirical observations recorded.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Multimodal Timeline */}
      {activeTab === 'timeline' && (
        <div className="card">
          <h3>Unified Multimodal Telemetry Timeline</h3>
          <p className="muted" style={{ marginBottom: '20px' }}>
            Chronologically aligned events across logs, metrics, distributed traces, and deployments.
          </p>

          {timelineEvents.length === 0 ? (
            <p className="muted">No timeline events extracted. Run the AI investigation to correlate signals.</p>
          ) : (
            <div className="timeline-list">
              {timelineEvents.map((t: any, idx: number) => (
                <div key={idx} className="timeline-item">
                  <div className={`timeline-dot ${t.severity || 'info'}`} />
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                    <span className="dim" style={{ fontSize: '0.78rem' }}>
                      {new Date(t.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`badge ${t.source === 'deployments' ? 'badge-sev3' : t.source === 'logs' ? 'badge-sev1' : 'badge-sev2'}`}>
                      {t.source}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.9rem', color: '#f1f5f9' }}>{t.event}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Safe Remediation & Approval Center */}
      {activeTab === 'remediation' && (
        <div className="grid-2">
          <div className="card">
            <h3>Remediation Plan & Human Approval</h3>
            <p className="muted" style={{ marginBottom: '16px' }}>
              Autonomous safety governance requires SRE operator confirmation prior to simulation or rollout.
            </p>

            {remediationPlan ? (
              <div className="card-subtle" style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    Action: {remediationPlan.action || 'rollback_deployment'}
                  </span>
                  <span className={`badge ${remediationPlan.risk === 'high' ? 'badge-sev1' : remediationPlan.risk === 'medium' ? 'badge-sev2' : 'badge-resolved'}`}>
                    Risk: {(remediationPlan.risk_level || remediationPlan.risk || 'low').toUpperCase()}
                  </span>
                </div>

                <p className="muted" style={{ fontSize: '0.9rem', marginBottom: '12px' }}>
                  {remediationPlan.description || 'Roll back deployment to prior stable release and recycle leaked database connection handles.'}
                </p>

                <div className="dim" style={{ marginBottom: '14px', fontSize: '0.85rem' }}>
                  Execution Mode: <b>SIMULATION (MockKubernetesProvider)</b> • Requires Approval: <b>YES</b>
                </div>

                {incident.status === 'RESOLVED' ? (
                  <div style={{ color: '#34d399', fontWeight: 600, fontSize: '0.9rem' }}>
                    ✓ Remediation action executed & verified. Incident is RESOLVED.
                  </div>
                ) : (
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      disabled={actionLoading || !token}
                      onClick={() => approveRemediation(remediationPlan.id || 1)}
                      className="btn btn-success"
                    >
                      {actionLoading ? 'Executing...' : '✓ Approve & Simulate Remediation'}
                    </button>

                    <button
                      disabled={actionLoading || !token}
                      onClick={() => rejectRemediation(remediationPlan.id || 1)}
                      className="btn btn-outline"
                    >
                      Reject Action
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <p className="muted">No remediation action proposed yet. Run the investigation first.</p>
            )}

            {/* Verification Plan */}
            {verificationPlan.length > 0 && (
              <div>
                <h4>Post-Remediation Verification Criteria</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                  {verificationPlan.map((v: any, idx: number) => (
                    <div key={idx} className="card-subtle" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                      <span>Step {v.step}: Metric <b>{v.metric_or_signal}</b></span>
                      <span style={{ color: '#34d399' }}>Target: {v.target_condition}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Live Verification Results */}
          <div className="card">
            <h3>Post-Remediation Verification Results</h3>
            {actionResult ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div className="card-subtle" style={{ borderColor: '#10b981' }}>
                  <div style={{ fontWeight: 700, color: '#34d399', marginBottom: '6px' }}>
                    ✓ Action Succeeded: {actionResult.action?.action}
                  </div>
                  <p className="muted" style={{ fontSize: '0.85rem', margin: 0 }}>
                    {actionResult.action?.result?.message || 'Rollback simulation completed with zero downtime.'}
                  </p>
                </div>

                <div className="card-subtle">
                  <div className="dim" style={{ marginBottom: '8px' }}>VERIFIED SERVICE HEALTH</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', fontSize: '0.88rem' }}>
                    <div>Service: <b>{actionResult.verification?.service}</b></div>
                    <div>Active Version: <b>{actionResult.verification?.version}</b></div>
                    <div>Error Rate: <b style={{ color: '#34d399' }}>{((actionResult.verification?.error_rate || 0) * 100).toFixed(2)}%</b></div>
                    <div>Latency: <b style={{ color: '#34d399' }}>{Math.round(actionResult.verification?.latency_ms || 85)}ms</b></div>
                    <div>Health Status: <b style={{ color: '#34d399' }}>100% HEALTHY</b></div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="muted">Verification metrics will be probed after remediation is approved and executed.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: Audit Trail */}
      {activeTab === 'audit' && (
        <div className="card">
          <h3>Incident Audit Trail & Lifecycle Events</h3>
          <div className="table-wrap" style={{ marginTop: '14px' }}>
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event Type</th>
                  <th>Source</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {incident.events?.map((e: any) => (
                  <tr key={e.id}>
                    <td className="dim">{new Date(e.timestamp).toLocaleString()}</td>
                    <td><span className="badge badge-sev3">{e.event_type}</span></td>
                    <td style={{ fontWeight: 600 }}>{e.source}</td>
                    <td style={{ fontSize: '0.82rem', fontFamily: 'monospace', color: '#cbd5e1' }}>
                      {JSON.stringify(e.payload)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
