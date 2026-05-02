import React, { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../App';
import { api } from '../../utils/api';

const NAV_ITEMS = [
  { path: '/', icon: '🏠', label: 'Dashboard' },
  { path: '/predictions', icon: '🔮', label: 'Predictions' },
  { path: '/recommendations', icon: '📋', label: 'Recommendations' },
  { path: '/reports', icon: '📊', label: 'Reports' },
  { path: '/admin', icon: '⚙️', label: 'Admin', role: 'admin' },
];

function Sidebar({ collapsed }) {
  const location = useLocation();
  const { user } = useAuth();
  return (
    <aside style={{
      width: collapsed ? 56 : 'var(--sidebar-width)',
      background: 'var(--green-900)',
      height: '100vh',
      display: 'flex', flexDirection: 'column',
      position: 'fixed', left: 0, top: 0, bottom: 0,
      transition: 'width 0.2s ease',
      zIndex: 100, overflowX: 'hidden',
    }}>
      {/* Logo */}
      <div style={{
        height: 'var(--header-height)', display: 'flex', alignItems: 'center',
        padding: collapsed ? '0 12px' : '0 16px', gap: 10,
        borderBottom: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ fontSize: 24, flexShrink: 0 }}>🌾</div>
        {!collapsed && (
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--green-300)', lineHeight: 1.2 }}>AgriPrice</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Intelligence System</div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        {NAV_ITEMS.map(item => {
          if (item.role && user?.role !== item.role) return null;
          const active = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
          return (
            <Link key={item.path} to={item.path} style={{ textDecoration: 'none' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: collapsed ? '10px 12px' : '10px 12px',
                borderRadius: 'var(--radius-md)',
                background: active ? 'rgba(255,255,255,0.12)' : 'transparent',
                color: active ? 'var(--green-200)' : 'rgba(255,255,255,0.55)',
                fontSize: 13, fontWeight: active ? 600 : 400,
                transition: 'all 0.15s',
                cursor: 'pointer',
              }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              >
                <span style={{ fontSize: 16, flexShrink: 0 }}>{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      {!collapsed && user && (
        <div style={{
          padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.08)',
        }}>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
            Logged in as
          </div>
          <div style={{ color: 'var(--green-200)', fontWeight: 600, fontSize: 13 }}>{user.username}</div>
          <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11 }}>{user.role?.toUpperCase()}</div>
        </div>
      )}
    </aside>
  );
}

function Header({ collapsed, setCollapsed, alerts }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [showNotifs, setShowNotifs] = useState(false);

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <header style={{
      position: 'fixed', top: 0, left: collapsed ? 56 : 'var(--sidebar-width)',
      right: 0, height: 'var(--header-height)',
      background: 'var(--white)', borderBottom: '1px solid var(--neutral-200)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 20px', zIndex: 99, transition: 'left 0.2s ease',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={() => setCollapsed(!collapsed)} className="btn btn-secondary btn-sm"
          style={{ padding: '6px 8px' }}>
          {collapsed ? '▶' : '◀'}
        </button>
        <div>
          <div style={{ fontSize: 11, color: 'var(--neutral-500)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Ministry of Consumer Affairs · Food & Public Distribution
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* System health indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', background: 'var(--green-50)', borderRadius: 20, border: '1px solid var(--green-200)' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green-500)', animation: 'pulse 2s ease infinite' }} />
          <span style={{ fontSize: 11, color: 'var(--green-700)', fontWeight: 600 }}>System Online</span>
        </div>

        {/* Notifications */}
        <div style={{ position: 'relative' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setShowNotifs(!showNotifs)}
            style={{ position: 'relative' }}>
            🔔
            {alerts.length > 0 && (
              <span style={{
                position: 'absolute', top: -4, right: -4,
                width: 16, height: 16, borderRadius: '50%',
                background: 'var(--red-600)', color: 'white',
                fontSize: 10, fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {Math.min(alerts.length, 9)}
              </span>
            )}
          </button>
          {showNotifs && (
            <div style={{
              position: 'absolute', right: 0, top: 36, width: 300, zIndex: 200,
              background: 'var(--white)', border: '1px solid var(--neutral-200)',
              borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)',
              maxHeight: 400, overflow: 'auto',
            }}>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--neutral-100)', fontWeight: 600, fontSize: 13 }}>
                Alerts ({alerts.length})
              </div>
              {alerts.length === 0 ? (
                <div style={{ padding: 20, textAlign: 'center', color: 'var(--neutral-500)', fontSize: 13 }}>No active alerts</div>
              ) : alerts.slice(0, 8).map(a => (
                <div key={a.id} style={{ padding: '10px 14px', borderBottom: '1px solid var(--neutral-100)' }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--neutral-800)' }}>{a.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--neutral-500)', marginTop: 2 }}>{a.message?.slice(0, 80)}...</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <button className="btn btn-secondary btn-sm" onClick={handleLogout}>Logout</button>
      </div>
    </header>
  );
}

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await api.get('/alerts/active');
        setAlerts(data || []);
      } catch {}
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <Sidebar collapsed={collapsed} />
      <Header collapsed={collapsed} setCollapsed={setCollapsed} alerts={alerts} />
      <main style={{
        marginLeft: collapsed ? 56 : 'var(--sidebar-width)',
        marginTop: 'var(--header-height)',
        minHeight: `calc(100vh - var(--header-height))`,
        transition: 'margin-left 0.2s ease',
      }}>
        <Outlet />
      </main>
    </div>
  );
}
