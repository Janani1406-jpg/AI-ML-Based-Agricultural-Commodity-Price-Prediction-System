import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { api } from '../utils/api';
import AlertsBanner from '../components/dashboard/AlertsBanner';

const COMMODITIES = [
  { id: 'onion', label: 'Onion', icon: '🧅', color: '#8b5cf6' },
  { id: 'potato', label: 'Potato', icon: '🥔', color: '#f59e0b' },
  { id: 'tomato', label: 'Tomato', icon: '🍅', color: '#ef4444' },
  { id: 'gram', label: 'Gram', icon: '🫘', color: '#10b981' },
  { id: 'tur', label: 'Tur Dal', icon: '🌾', color: '#f97316' },
  { id: 'urad', label: 'Urad Dal', icon: '⚪', color: '#6b7280' },
  { id: 'moong', label: 'Moong', icon: '🟢', color: '#84cc16' },
  { id: 'masur', label: 'Masur', icon: '🟠', color: '#fb923c' },
];

function ConfidenceMeter({ score }) {
  const cls = score >= 80 ? 'confidence-high' : score >= 65 ? 'confidence-med' : 'confidence-low';
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span className="text-sm text-muted">Confidence</span>
        <span className="text-sm" style={{ fontWeight: 600 }}>{score?.toFixed(0)}%</span>
      </div>
      <div className={`confidence-bar ${cls}`}>
        <div className="confidence-fill" style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

function Sparkline({ data, color }) {
  if (!data?.length) return null;
  return (
    <ResponsiveContainer width="100%" height={40}>
      <AreaChart data={data.map((v, i) => ({ v, i }))} margin={{ top: 2, bottom: 2, left: 0, right: 0 }}>
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.25} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5}
          fill={`url(#grad-${color})`} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function CommodityCard({ commodity, stats, prediction }) {
  const navigate = useNavigate();
  const pct = prediction?.explanation?.price_change_pct ?? 0;
  const isUp = pct > 0;
  const isDown = pct < 0;

  return (
    <div
      className="card"
      style={{ cursor: 'pointer', transition: 'box-shadow 0.15s', overflow: 'hidden' }}
      onClick={() => navigate(`/commodities/${commodity.id}`)}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = ''}
    >
      {/* Top accent bar */}
      <div style={{ height: 3, background: commodity.color }} />

      <div style={{ padding: 16 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="commodity-icon" style={{ background: commodity.color + '18' }}>
              {commodity.icon}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{commodity.label}</div>
              <div className="text-sm text-muted">Per kg (modal)</div>
            </div>
          </div>
          {pct !== 0 && (
            <span className={`badge ${isUp ? 'badge-red' : 'badge-green'}`} style={{ fontSize: 13 }}>
              {isUp ? '↑' : '↓'} {Math.abs(pct).toFixed(1)}%
            </span>
          )}
        </div>

        {/* Current Price */}
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'var(--font-mono)', lineHeight: 1 }}>
            ₹{stats?.current_price?.toFixed(2) ?? '—'}
          </div>
          <div className="text-sm text-muted" style={{ marginTop: 2 }}>
            {stats?.price_change_1d >= 0 ? '+' : ''}
            {stats?.price_change_1d?.toFixed(2) ?? '—'} today
          </div>
        </div>

        {/* Sparkline */}
        <div style={{ marginBottom: 12 }}>
          <Sparkline data={stats?.sparkline ?? []} color={commodity.color} />
        </div>

        {/* Prediction */}
        {prediction && (
          <div style={{
            background: isUp ? 'var(--red-100)' : isDown ? 'var(--green-50)' : 'var(--neutral-100)',
            borderRadius: 'var(--radius-md)', padding: '10px 12px', marginBottom: 12,
          }}>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--neutral-500)', marginBottom: 4 }}>
              7-Day Forecast
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700 }}>
                ₹{prediction.predicted_price?.toFixed(2)}
              </span>
              <span style={{ fontSize: 12, color: isUp ? 'var(--red-600)' : 'var(--green-600)', fontWeight: 600 }}>
                {isUp ? '▲' : '▼'} {Math.abs(pct).toFixed(1)}%
              </span>
            </div>
            <div className="text-sm text-muted" style={{ marginTop: 2 }}>
              ₹{prediction.lower_bound?.toFixed(1)} – ₹{prediction.upper_bound?.toFixed(1)} range
            </div>
          </div>
        )}

        <ConfidenceMeter score={prediction?.confidence_score ?? 0} />
      </div>
    </div>
  );
}

function SummaryStats({ allStats, allPredictions }) {
  const avgConfidence = allPredictions.length
    ? allPredictions.reduce((s, p) => s + (p?.confidence_score ?? 0), 0) / allPredictions.length
    : 0;
  const spikeCount = allPredictions.filter(p => (p?.explanation?.price_change_pct ?? 0) >= 15).length;
  const activeAlerts = allPredictions.filter(p => p?.is_flagged).length;

  return (
    <div className="grid-4" style={{ marginBottom: 24 }}>
      {[
        { label: 'Avg Confidence', value: `${avgConfidence.toFixed(0)}%`, icon: '🎯', color: 'var(--green-500)' },
        { label: 'Price Spike Alerts', value: spikeCount, icon: '⚠️', color: 'var(--amber-500)' },
        { label: 'Flagged Predictions', value: activeAlerts, icon: '🚨', color: 'var(--red-600)' },
        { label: 'Commodities Tracked', value: '8', icon: '📊', color: 'var(--blue-500)' },
      ].map(stat => (
        <div key={stat.label} className="card">
          <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 28 }}>{stat.icon}</div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 700, fontFamily: 'var(--font-mono)', color: stat.color }}>
                {stat.value}
              </div>
              <div className="text-sm text-muted">{stat.label}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState({});
  const [predictions, setPredictions] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, predsRes, alertsRes] = await Promise.allSettled([
        api.get('/commodities/stats/all'),
        api.post('/predictions/batch', { commodities: COMMODITIES.map(c => c.id), horizon_days: 7 }),
        api.get('/alerts/active'),
      ]);

      if (statsRes.status === 'fulfilled') {
        const statsMap = {};
        statsRes.value.forEach(s => { statsMap[s.commodity] = s; });
        setStats(statsMap);
      }

      if (predsRes.status === 'fulfilled') {
        const predMap = {};
        predsRes.value.predictions?.forEach(p => { if (p.commodity) predMap[p.commodity] = p; });
        setPredictions(predMap);
      }

      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value || []);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5 * 60 * 1000); // Refresh every 5 min
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) return (
    <div style={{ padding: 32 }}>
      <div className="grid-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="card" style={{ height: 220 }}>
            <div style={{ padding: 16 }}>
              {[...Array(4)].map((_, j) => (
                <div key={j} style={{
                  height: j === 2 ? 40 : 16, background: 'var(--neutral-200)',
                  borderRadius: 4, marginBottom: 12, width: j === 1 ? '60%' : '100%',
                  animation: 'pulse 1.5s ease infinite'
                }} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--neutral-900)' }}>
            Price Intelligence Dashboard
          </h1>
          <p className="text-muted text-sm">
            Real-time predictions for 8 essential agricultural commodities
            {lastUpdated && ` · Updated ${lastUpdated.toLocaleTimeString()}`}
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchData}>
          🔄 Refresh
        </button>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && <AlertsBanner alerts={alerts.slice(0, 3)} />}

      {/* Summary Stats */}
      <SummaryStats allStats={stats} allPredictions={Object.values(predictions)} />

      {/* Commodity Grid */}
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: 'var(--neutral-700)' }}>Commodity Overview</h2>
        <span className="text-sm text-muted">Click a card for detailed analysis →</span>
      </div>
      <div className="grid-4">
        {COMMODITIES.map(commodity => (
          <CommodityCard
            key={commodity.id}
            commodity={commodity}
            stats={stats[commodity.id]}
            prediction={predictions[commodity.id]}
          />
        ))}
      </div>
    </div>
  );
}
