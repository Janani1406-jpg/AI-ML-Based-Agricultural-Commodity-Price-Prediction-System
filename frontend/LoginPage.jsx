import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { api } from '../utils/api';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '', totp_code: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showTotp, setShowTotp] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await api.auth.login(form);
      login(data.access_token, data.user || { username: form.username, role: 'admin' });
      navigate('/');
    } catch (err) {
      if (err.status === 428) {
        setShowTotp(true);
        setError('Please enter your two-factor authentication code.');
      } else {
        setError('Invalid username or password.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, var(--green-900) 0%, var(--green-700) 60%, var(--green-500) 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'var(--font-sans)',
    }}>
      {/* Background texture */}
      <div style={{
        position: 'fixed', inset: 0, opacity: 0.05,
        backgroundImage: 'repeating-linear-gradient(45deg, #fff 0, #fff 1px, transparent 0, transparent 50%)',
        backgroundSize: '20px 20px',
      }} />

      <div style={{ width: 420, position: 'relative', zIndex: 1 }}>
        {/* Logo block */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 56, marginBottom: 8 }}>🌾</div>
          <h1 style={{ color: '#fff', fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
            AgriPrice Intelligence
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>
            Ministry of Consumer Affairs · Government of India
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: 'rgba(255,255,255,0.97)',
          borderRadius: 'var(--radius-xl)',
          padding: 32,
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4, color: 'var(--neutral-800)' }}>
            Sign In
          </h2>
          <p style={{ color: 'var(--neutral-500)', fontSize: 13, marginBottom: 24 }}>
            Enter your official credentials to access the dashboard.
          </p>

          {error && (
            <div className="alert-banner alert-critical" style={{ marginBottom: 16 }}>
              ⚠️ {error}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input
                type="text" className="form-control"
                value={form.username}
                onChange={e => setForm(p => ({ ...p, username: e.target.value }))}
                placeholder="Enter username"
                autoComplete="username"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password" className="form-control"
                value={form.password}
                onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                placeholder="Enter password"
                autoComplete="current-password"
                required
              />
            </div>
            {showTotp && (
              <div className="form-group">
                <label className="form-label">2FA Code</label>
                <input
                  type="text" className="form-control"
                  value={form.totp_code}
                  onChange={e => setForm(p => ({ ...p, totp_code: e.target.value }))}
                  placeholder="6-digit code from authenticator"
                  maxLength={6}
                />
              </div>
            )}
            <button
              type="submit" className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', padding: '11px 0', fontSize: 14, marginTop: 4 }}
              disabled={loading}
            >
              {loading ? 'Signing in…' : 'Sign In →'}
            </button>
          </form>

          <div style={{ marginTop: 20, padding: 12, background: 'var(--neutral-50)', borderRadius: 'var(--radius-md)', fontSize: 12, color: 'var(--neutral-500)', textAlign: 'center' }}>
            🔒 Secure government system. All access is logged and monitored.
          </div>
        </div>

        {/* Demo credentials hint */}
        <div style={{ textAlign: 'center', marginTop: 16, color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>
          Demo: admin / Admin@123 (admin) · analyst / Analyst@123 (analyst)
        </div>
      </div>
    </div>
  );
}
