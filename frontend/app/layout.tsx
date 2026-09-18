'use client';
import './globals.css';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [token, setToken] = useState<string | null>(null);
  const [health, setHealth] = useState<{ status: string; model_provider?: string; model_name?: string } | null>(null);

  useEffect(() => {
    const t = localStorage.getItem('token');
    setToken(t);

    fetch(`${API}/api/v1/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setHealth(d))
      .catch(() => setHealth(null));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    window.location.href = '/login';
  };

  const navLinks = [
    { href: '/', label: 'Dashboard' },
    { href: '/incidents', label: 'Incidents' },
    { href: '/services', label: 'Services' },
    { href: '/knowledge', label: 'Knowledge (RAG)' },
    { href: '/observability', label: 'Observability' },
    { href: '/audit', label: 'Audit Log' },
    { href: '/settings', label: 'Settings' },
  ];

  return (
    <html lang="en">
      <head>
        <title>MultiModal-SRE | Autonomous AI SRE Platform</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <div className="app-container">
          <header className="header-nav">
            <div className="nav-wrapper">
              <div style={{ display: 'flex', alignItems: 'center', gap: '28px' }}>
                <Link href="/" className="brand">
                  <div className="brand-icon">⚡</div>
                  <span>MultiModal<span style={{ color: '#38bdf8' }}>-SRE</span></span>
                </Link>

                <nav className="nav-links">
                  {navLinks.map((l) => (
                    <Link
                      key={l.href}
                      href={l.href}
                      className={`nav-link ${pathname === l.href ? 'active' : ''}`}
                    >
                      {l.label}
                    </Link>
                  ))}
                </nav>
              </div>

              <div className="nav-actions">
                <div className="engine-badge">
                  <div className="engine-dot" />
                  <span>AI: {health?.model_provider || 'Deterministic'}</span>
                </div>

                {token ? (
                  <button onClick={handleLogout} className="btn btn-outline btn-sm">
                    Sign Out
                  </button>
                ) : (
                  <Link href="/login" className="btn btn-primary btn-sm">
                    Sign In
                  </Link>
                )}
              </div>
            </div>
          </header>

          <main className="main-content">{children}</main>
        </div>
      </body>
    </html>
  );
}
