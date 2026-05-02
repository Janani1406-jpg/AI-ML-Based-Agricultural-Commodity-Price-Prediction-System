import React, { useState } from 'react';

const SEVERITY_STYLE = {
  critical: { cls: 'alert-critical', icon: '🚨' },
  high:     { cls: 'alert-high',     icon: '⚠️' },
  medium:   { cls: 'alert-medium',   icon: '⚡' },
  low:      { cls: 'alert-low',      icon: 'ℹ️' },
};

export default function AlertsBanner({ alerts }) {
  const [dismissed, setDismissed] = useState([]);
  const visible = alerts.filter(a => !dismissed.includes(a.id));
  if (!visible.length) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
      {visible.map(alert => {
        const style = SEVERITY_STYLE[alert.severity] || SEVERITY_STYLE.medium;
        return (
          <div key={alert.id} className={`alert-banner ${style.cls}`}>
            <span style={{ fontSize: 18, flexShrink: 0 }}>{style.icon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{alert.title}</div>
              <div style={{ fontSize: 12, opacity: 0.85 }}>{alert.message}</div>
            </div>
            <button
              onClick={() => setDismissed(d => [...d, alert.id])}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', opacity: 0.6, fontSize: 16, flexShrink: 0 }}>
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
