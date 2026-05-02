import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts';
import { api, COMMODITY_COLORS } from '../utils/api';

const COMMODITY_META = {
  onion:  { label: 'Onion',   icon: '🧅', unit: '₹/kg' },
  potato: { label: 'Potato',  icon: '🥔', unit: '₹/kg' },
  tomato: { label: 'Tomato',  icon: '🍅', unit: '₹/kg' },
  gram:   { label: 'Gram',    icon: '🫘', unit: '₹/kg', hasMsp: true },
  tur:    { label: 'Tur Dal', icon: '🌾', unit: '₹/kg', hasMsp: true },
  urad:   { label: 'Urad Dal',icon: '⚪', unit: '₹/kg', hasMsp: true },
  moong:  { label: 'Moong',   icon: '🟢', unit: '₹/kg', hasMsp: true },
  masur:  { label: 'Masur',   icon: '🟠', unit: '₹/kg', hasMsp: true },
};

const TABS = ['Overview', 'History', 'Predictions', 'Alerts'];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--white)', border: '1px solid var(--neutral-200)',
      borderRadius: 'var(--radius-md)', padding: '10px 14px', boxShadow: 'var(--shadow-md)', fontSize: 12,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 2 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color }} />
          <span style={{ color: 'var(--neutral-600)' }}>{p.name}:</span>
          <span style={{ fontWeight: 600 }}>₹{p.value?.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}

function StatCard({ label, value, sub, icon, color }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <span className="text-sm text-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em', fontSize: 11 }}>{label}</span>
        <span style={{ fontSize: 20 }}>{icon}</span>
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color: color || 'var(--neutral-800)' }}>
        {value}
      </div>
      {sub && <div className="text-sm text-muted" style={{ marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

export default function CommodityDetail() {
  const { commodity } = useParams();
  const [tab, setTab] = useState('Overview');
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [histDays, setHistDays] = useState(90);
  const meta = COMMODITY_META[commodity] || { label: commodity, icon: '🌿', unit: '₹/kg' };
  const color = COMMODITY_COLORS[commodity] || 'var(--green-500)';

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [s, h, p, a] = await Promise.allSettled([
          api.get(`/commodities/${commodity}/stats`),
          api.get(`/commodities/${commodity}/history?days=${histDays}`),
          api.get(`/predictions/latest/${commodity}`),
          api.get(`/alerts/active?commodity=${commodity}`),
        ]);
        if (s.status === 'fulfilled') setStats(s.value);
        if (h.status === 'fulfilled') setHistory(h.value?.data || []);
        if (p.status === 'fulfilled') setPredictions(p.value || []);
        if (a.status === 'fulfilled') setAlerts(a.value || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, [commodity, histDays]);

  // Merge history + forecast for combined chart
  const chartData = [
    ...history.slice(-60).map(h => ({
      date: new Date(h.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
      actual: h.modal_price,
      type: 'actual',
    })),
    ...predictions.map(p => ({
      date: new Date(p.target_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
      forecast: p.predicted_price,
      lower: p.lower_bound,
      upper: p.upper_bound,
      type: 'forecast',
    })),
  ];

  if (loading) return (
    <div style={{ padding: 32, display: 'flex', justifyContent: 'center' }}>
      <div className="spinner" />
    </div>
  );

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24 }}>
        <div style={{
          width: 52, height: 52, borderRadius: 'var(--radius-lg)',
          background: color + '20', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28,
        }}>
          {meta.icon}
        </div>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--neutral-900)' }}>{meta.label}</h1>
          <p className="text-muted text-sm">Detailed price analysis and multi-horizon forecasts</p>
        </div>
        {meta.hasMsp && <span className="badge badge-blue" style={{ marginLeft: 'auto' }}>MSP Regulated</span>}
      </div>

      {/* Top stats */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <StatCard label="Current Price" value={stats?.current_price ? `₹${stats.current_price.toFixed(2)}` : '—'}
          sub={`Last updated today`} icon="💰" />
        <StatCard label="1-Day Change" value={stats?.price_change_1d != null ? `${stats.price_change_1d >= 0 ? '+' : ''}₹${stats.price_change_1d.toFixed(2)}` : '—'}
          icon={stats?.price_change_1d >= 0 ? '📈' : '📉'}
          color={stats?.price_change_1d >= 0 ? 'var(--red-600)' : 'var(--green-600)'} />
        <StatCard label="7-Day Change" value={stats?.price_change_7d != null ? `${stats.price_change_7d >= 0 ? '+' : ''}₹${stats.price_change_7d.toFixed(2)}` : '—'}
          icon="📅"
          color={stats?.price_change_7d >= 0 ? 'var(--red-600)' : 'var(--green-600)'} />
        <StatCard label="Avg Arrivals (7d)" value={stats?.avg_arrivals_7d ? `${stats.avg_arrivals_7d.toFixed(0)} T` : '—'}
          icon="🚛" sub="tonnes/day" />
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '2px solid var(--neutral-200)', marginBottom: 20 }}>
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '10px 20px', background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: tab === t ? 600 : 400,
              color: tab === t ? color : 'var(--neutral-500)',
              borderBottom: tab === t ? `2px solid ${color}` : '2px solid transparent',
              marginBottom: -2, transition: 'all 0.15s',
            }}
          >
            {t}
            {t === 'Alerts' && alerts.length > 0 && (
              <span style={{ marginLeft: 6, background: 'var(--red-600)', color: '#fff', borderRadius: 10, padding: '1px 6px', fontSize: 10 }}>
                {alerts.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'Overview' && (
        <div>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <span className="card-title">Price Trend with Forecast</span>
              <div style={{ display: 'flex', gap: 6 }}>
                {[30, 60, 90].map(d => (
                  <button key={d} className={`btn btn-sm ${histDays === d ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setHistDays(d)}>
                    {d}d
                  </button>
                ))}
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="grad-actual" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={color} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="grad-forecast" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--neutral-200)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${v}`} width={55} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Area type="monotone" dataKey="actual" name="Actual Price" stroke={color}
                    strokeWidth={2} fill="url(#grad-actual)" dot={false} connectNulls />
                  <Area type="monotone" dataKey="forecast" name="Forecast" stroke="#3b82f6"
                    strokeDasharray="5 4" strokeWidth={2} fill="url(#grad-forecast)" dot={false} connectNulls />
                  {/* Forecast range band */}
                  <Area type="monotone" dataKey="upper" name="Upper Bound" stroke="none"
                    fill="#3b82f620" dot={false} connectNulls legendType="none" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {tab === 'History' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Price History</span>
            <div style={{ display: 'flex', gap: 6 }}>
              {[30, 90, 180, 365].map(d => (
                <button key={d} className={`btn btn-sm ${histDays === d ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setHistDays(d)}>
                  {d >= 365 ? '1Y' : `${d}d`}
                </button>
              ))}
            </div>
          </div>
          <div className="card-body">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th className="text-right">Modal Price</th>
                    <th className="text-right">Min Price</th>
                    <th className="text-right">Max Price</th>
                    <th className="text-right">Arrivals (T)</th>
                    <th>Market</th>
                  </tr>
                </thead>
                <tbody>
                  {history.slice(0, 50).map((row, i) => (
                    <tr key={i}>
                      <td>{new Date(row.date).toLocaleDateString('en-IN')}</td>
                      <td className="text-right text-mono" style={{ fontWeight: 600 }}>₹{row.modal_price?.toFixed(2)}</td>
                      <td className="text-right text-mono" style={{ color: 'var(--neutral-500)' }}>₹{row.min_price?.toFixed(2) || '—'}</td>
                      <td className="text-right text-mono" style={{ color: 'var(--neutral-500)' }}>₹{row.max_price?.toFixed(2) || '—'}</td>
                      <td className="text-right text-mono">{row.arrivals_tonnes?.toFixed(0) || '—'}</td>
                      <td>{row.market}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === 'Predictions' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {predictions.length === 0 ? (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <div style={{ fontSize: 36, marginBottom: 10 }}>🔮</div>
              <div style={{ fontWeight: 600 }}>No predictions available</div>
              <div className="text-muted text-sm">Go to Predictions page to generate forecasts.</div>
            </div>
          ) : predictions.map(p => (
            <div key={p.id} className="card">
              <div style={{ padding: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', gap: 12 }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: 'var(--radius-md)',
                    background: 'var(--green-50)', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 15, color,
                  }}>
                    {p.horizon_days}d
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>
                      ₹{p.predicted_price?.toFixed(2)}/kg in {p.horizon_days} days
                    </div>
                    <div className="text-sm text-muted">
                      Range: ₹{p.lower_bound?.toFixed(2)} – ₹{p.upper_bound?.toFixed(2)} ·
                      Scenario: {p.scenario}
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color }}>
                    {p.confidence_score?.toFixed(0)}%
                  </div>
                  <div className="text-sm text-muted">confidence</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'Alerts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {alerts.length === 0 ? (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <div style={{ fontSize: 36, marginBottom: 10 }}>✅</div>
              <div style={{ fontWeight: 600 }}>No active alerts</div>
              <div className="text-muted text-sm">Price levels are within normal range.</div>
            </div>
          ) : alerts.map(a => (
            <div key={a.id} className={`alert-banner alert-${a.severity}`}>
              <div>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{a.title}</div>
                <div style={{ fontSize: 12 }}>{a.message}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
