import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { useAuth } from '../App';

const RISK_STYLES = {
  high:   { color: 'var(--red-600)',    bg: 'var(--red-100)',    border: 'var(--red-600)',    label: 'HIGH RISK' },
  medium: { color: 'var(--amber-500)',  bg: 'var(--amber-100)',  border: 'var(--amber-500)',  label: 'MEDIUM RISK' },
  low:    { color: 'var(--green-600)',  bg: 'var(--green-50)',   border: 'var(--green-500)',  label: 'LOW RISK' },
};

const ACTION_ICONS = {
  release_buffer: '📤',
  procure: '📥',
  hold: '⏸️',
  monitor: '👁️',
};

function ExecuteModal({ recommendation, onClose, onExecute }) {
  const [notes, setNotes] = useState('');
  const [qty, setQty] = useState(recommendation.quantity_tonnes || '');
  const [loading, setLoading] = useState(false);
  const [checklist, setChecklist] = useState({ buffer: false, logistics: false, approved: false });

  const canExecute = Object.values(checklist).every(Boolean);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onExecute(recommendation.id, { notes, actual_quantity_tonnes: parseFloat(qty) });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div className="card" style={{ width: 480, maxHeight: '90vh', overflow: 'auto' }}>
        <div className="card-header">
          <span className="card-title">Execute Recommendation</span>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ padding: 12, background: 'var(--neutral-50)', borderRadius: 'var(--radius-md)', fontSize: 13 }}>
            {recommendation.headline}
          </div>

          <div className="form-group">
            <label className="form-label">Actual Quantity (tonnes)</label>
            <input type="number" className="form-control" value={qty}
              onChange={e => setQty(e.target.value)} placeholder="Enter quantity" />
          </div>

          <div>
            <div className="form-label" style={{ marginBottom: 8 }}>Execution Checklist</div>
            {[
              { key: 'buffer', label: 'Buffer stock availability verified' },
              { key: 'logistics', label: 'Logistics and transport confirmed' },
              { key: 'approved', label: 'Required approvals obtained' },
            ].map(item => (
              <label key={item.key} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', cursor: 'pointer', borderBottom: '1px solid var(--neutral-100)' }}>
                <input type="checkbox" checked={checklist[item.key]}
                  onChange={e => setChecklist(prev => ({ ...prev, [item.key]: e.target.checked }))}
                  style={{ width: 16, height: 16, accentColor: 'var(--green-600)' }} />
                <span style={{ fontSize: 13 }}>{item.label}</span>
              </label>
            ))}
          </div>

          <div className="form-group">
            <label className="form-label">Execution Notes</label>
            <textarea className="form-control" rows={3} value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Add any notes or deviations from recommended action..." />
          </div>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit}
              disabled={!canExecute || loading}>
              {loading ? 'Executing...' : '✓ Confirm Execution'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function RecommendationCard({ rec, onExecute, canExecute }) {
  const [expanded, setExpanded] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const risk = RISK_STYLES[rec.risk_level] || RISK_STYLES.medium;

  return (
    <>
      <div className="card" style={{ borderLeft: `4px solid ${risk.border}` }}>
        <div style={{ padding: 16 }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <div style={{ fontSize: 22, lineHeight: 1 }}>{ACTION_ICONS[rec.action_type] || '📋'}</div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--neutral-800)', marginBottom: 4 }}>
                  {rec.headline}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <span className="badge badge-gray">{rec.commodity?.toUpperCase()}</span>
                  <span style={{ background: risk.bg, color: risk.color }}
                    className="badge">
                    {risk.label}
                  </span>
                  <span className="badge badge-gray">
                    Conf: {rec.confidence_score?.toFixed(0)}%
                  </span>
                  <span className={`badge ${rec.status === 'executed' ? 'badge-green' : rec.status === 'dismissed' ? 'badge-gray' : 'badge-amber'}`}>
                    {rec.status?.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Key metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 12 }}>
            {[
              { label: 'Quantity', value: rec.quantity_tonnes ? `${rec.quantity_tonnes.toFixed(0)} T` : '—' },
              { label: 'Price Impact', value: rec.expected_price_impact ? `${rec.expected_price_impact > 0 ? '+' : ''}${rec.expected_price_impact.toFixed(1)}%` : '—' },
              { label: 'Markets', value: rec.target_markets?.length ? `${rec.target_markets.length} cities` : '—' },
            ].map(m => (
              <div key={m.label} style={{ textAlign: 'center', padding: '8px 0', background: 'var(--neutral-50)', borderRadius: 'var(--radius-md)' }}>
                <div style={{ fontSize: 11, color: 'var(--neutral-500)', textTransform: 'uppercase', fontWeight: 600 }}>{m.label}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 15, marginTop: 2 }}>{m.value}</div>
              </div>
            ))}
          </div>

          {/* Target markets */}
          {rec.target_markets?.length > 0 && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
              {rec.target_markets.map(m => (
                <span key={m} className="badge badge-blue">{m}</span>
              ))}
            </div>
          )}

          {/* Expandable detail */}
          {expanded && rec.detail && (
            <div style={{ fontSize: 13, color: 'var(--neutral-700)', lineHeight: 1.65, padding: '10px 12px', background: 'var(--neutral-50)', borderRadius: 'var(--radius-md)', marginBottom: 12 }}>
              {rec.detail}
            </div>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setExpanded(!expanded)}>
              {expanded ? '▲ Less' : '▼ Details'}
            </button>
            {rec.status === 'pending' && canExecute && (
              <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
                ✓ Execute
              </button>
            )}
            {rec.status === 'pending' && (
              <button className="btn btn-secondary btn-sm" style={{ color: 'var(--neutral-500)' }}>
                ✕ Dismiss
              </button>
            )}
            <span className="text-sm text-muted" style={{ marginLeft: 'auto' }}>
              {new Date(rec.generated_at).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {showModal && (
        <ExecuteModal
          recommendation={rec}
          onClose={() => setShowModal(false)}
          onExecute={onExecute}
        />
      )}
    </>
  );
}

export default function RecommendationsPage() {
  const { user } = useAuth();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [filter, setFilter] = useState('all');
  const canExecute = user?.role === 'admin' || user?.role === 'analyst';

  const fetchRecommendations = async () => {
    try {
      const data = await api.get('/recommendations/active');
      setRecommendations(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRecommendations(); }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await api.post('/recommendations/generate');
      await fetchRecommendations();
    } finally {
      setGenerating(false);
    }
  };

  const handleExecute = async (recId, payload) => {
    await api.put(`/recommendations/${recId}/execute`, payload);
    await fetchRecommendations();
  };

  const filtered = recommendations.filter(r => filter === 'all' || r.risk_level === filter || r.status === filter);
  const sorted = [...filtered].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.risk_level] ?? 3) - (order[b.risk_level] ?? 3);
  });

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Buffer Stock Recommendations</h1>
          <p className="text-muted text-sm">AI-generated recommendations for government intervention decisions.</p>
        </div>
        {canExecute && (
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
            {generating ? 'Generating...' : '⚡ Generate New'}
          </button>
        )}
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, borderBottom: '1px solid var(--neutral-200)', paddingBottom: 12 }}>
        {['all', 'high', 'medium', 'low', 'pending', 'executed'].map(f => (
          <button
            key={f}
            className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter(f)}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            <span style={{
              background: 'rgba(255,255,255,0.2)', borderRadius: 10,
              padding: '0 6px', fontSize: 10,
            }}>
              {f === 'all' ? recommendations.length : recommendations.filter(r => r.risk_level === f || r.status === f).length}
            </span>
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
      ) : sorted.length === 0 ? (
        <div className="card" style={{ padding: 48, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
          <div style={{ fontWeight: 600, color: 'var(--neutral-700)' }}>No recommendations found</div>
          <div className="text-sm text-muted" style={{ marginTop: 4 }}>
            Click "Generate New" to analyze latest predictions and create recommendations.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {sorted.map(rec => (
            <RecommendationCard key={rec.id} rec={rec} onExecute={handleExecute} canExecute={canExecute} />
          ))}
        </div>
      )}
    </div>
  );
}
