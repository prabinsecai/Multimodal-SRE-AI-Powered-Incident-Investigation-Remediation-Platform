'use client';
import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function LoginPage() {
  const [email, setEmail] = useState('admin@local');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        window.location.href = '/';
      } else {
        setError('Invalid credentials.');
      }
    } catch (err) {
      setError('Cannot reach authentication server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '440px', margin: '60px auto' }}>
      <div className="card">
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div className="brand-icon" style={{ width: '40px', height: '40px', margin: '0 auto 12px auto', fontSize: '20px' }}>
            ⚡
          </div>
          <h2>MultiModal-SRE Platform</h2>
          <p className="muted" style={{ fontSize: '0.88rem' }}>Sign in to access autonomous SRE incident operations</p>
        </div>

        {error && (
          <div className="card-subtle" style={{ borderColor: '#ef4444', color: '#f87171', marginBottom: '16px', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label className="dim" style={{ display: 'block', marginBottom: '4px' }}>Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="dim" style={{ display: 'block', marginBottom: '4px' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" disabled={loading} className="btn btn-primary" style={{ marginTop: '10px' }}>
            {loading ? 'Authenticating...' : 'Sign In to Workspace'}
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center', borderTop: '1px solid var(--border-color)', paddingTop: '14px' }}>
          <span className="dim">Demo Credentials: <code>admin@local</code> / <code>admin123</code></span>
        </div>
      </div>
    </div>
  );
}
