import React, { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine, LineChart, Line, Area, AreaChart
} from 'recharts';
import { api } from '../utils/api';

const COMMODITIES = ['onion', 'potato', 'tomato', 'gram', 'tur', 'urad', 'moong', 'masur'];
const HORIZONS = [
  { value: 7, label: '7 Days', desc: 'Short-term' },
  { value: 15, label: '15 Days', desc: 'Mid-term' },
  { value: 30, label: '30 Days', desc: 'Monthly' },
  { value: 90, label: '90 Days', desc: 'Quarterly' },
];
const SCENARIOS = [
  { value: 'baseline', label: 'Baseline', desc: 'Normal conditions', color: 'var(--green-600)' },
  { value: 'optimistic', label: 'Optimistic', desc: 'Good rainfall, high supply', color: 'var(--blue-500)' },
  { value: 'pessimistic', label: 'Pessimistic', desc: 'Drought, supply shock', color: 'var(--red-600)' },
];

function SHAPChart({ shap_values }) {
  if (!shap_values?.length) return null;
  const data = shap_values.map(s => ({
    feature: s.feature.replace(/_/g, ' '),
    impact: s.impact,
  }));
  return (
    <div>
      <div style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--neutral-500)', marginBottom: 8 }}>
        Price Drivers (SHAP)
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} layout="vertical" margin={{ left: 100, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--neutral-200)" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="feature" tick={{ fontSize: 11 }} width={100} />
          <Tooltip
            formatter={(val) => [`${val > 0 ? '+' : ''}₹${Math.abs(val).toFixed(2)}/kg`, 'Price Impact']}
          />
          <Bar dataKey="impact" radius={[0, 3, 3, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.impact > 0 ? 'var(--red-400)' : 'var(--green-400)'} />
            ))}
          </Bar>
          <ReferenceLine x={0} stroke="var(--neutral-400)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function PredictionResult({ result, currentPrice }) {
  const pct = result.explanation?.price_change_pct ?? 0;
  const isUp = pct > 0;

  return (
    <div className="card" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="card-header">
        <span className="card-title">Prediction Result</span>
        <span className={`badge ${isUp ? 'badge-red' : 'badge-green'}`}>
          {isUp ? '▲' : '▼'} {Math.abs(pct).toFixed(1)}%
        </span>
      </div>
      <div className="card-body">
        {/* Price display */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 20 }}>
          {[
            { label: 'Current Price', value: `₹${currentPrice?.toFixed(2) ?? '—'}`, color: 'var(--neutral-800)' },
            { label: 'Predicted Price', value: `₹${result.predicted_price?.toFixed(2)}`, color: isUp ? 'var(--red-600)' : 'var(--green-600)' },
            { label: 'Confidence', value: `${result.confidence_score?.toFixed(0)}%`, color: 'var(--green-600)' },
          ].map(item => (
            <div key={item.label} style={{
              textAlign: 'center', padding: '14px 8px',
              background: 'var(--neutral-50)', borderRadius: 'var(--radius-md)',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--neutral-500)', marginBottom: 4 }}>
                {item.label}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color: item.color }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>

        {/* Price range */}
        <div style={{ padding: '12px 14px', background: 'var(--neutral-50)', borderRadius: 'var(--radius-md)', marginBottom: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--neutral-500)', marginBottom: 6 }}>
            80% Confidence Interval
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--green-600)', fontWeight: 600 }}>
              ₹{result.lower_bound?.toFixed(2)}
            </span>
            <div style={{ flex: 1, height: 6, background: 'var(--neutral-200)', borderRadius: 3, position: 'relative' }}>
              <div style={{
                position: 'absolute',
                left: `${((result.predicted_price - result.lower_bound) / (result.upper_bound - result.lower_bound)) * 100}%`,
                top: -3, width: 12, height: 12, borderRadius: '50%',
                background: 'var(--green-600)', transform: 'translateX(-50%)',
              }} />
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--red-600)', fontWeight: 600 }}>
              ₹{result.upper_bound?.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Explanation */}
        {result.explanation?.text && (
          <div style={{
            padding: '12px 14px', background: 'var(--green-50)',
            borderLeft: '3px solid var(--green-500)', borderRadius: 'var(--radius-sm)', marginBottom: 16,
            fontSize: 13, color: 'var(--neutral-700)', lineHeight: 1.6,
          }}>
            {result.explanation.text}
          </div>
        )}

        {/* SHAP chart */}
        <SHAPChart shap_values={result.shap_values} />

        {/* Model breakdown */}
        {result.model_components && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--neutral-500)', marginBottom: 8 }}>
              Model Breakdown
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
              {Object.entries(result.model_components).map(([model, value]) => (
                <div key={model} style={{ textAlign: 'center', padding: '10px 8px', border: '1px solid var(--neutral-200)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: 11, color: 'var(--neutral-500)', textTransform: 'uppercase' }}>{model.toUpperCase()}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, marginTop: 2 }}>₹{value?.toFixed(2)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PredictionsPage() {
  const [commodity, setCommodity] = useState('onion');
  const [horizon, setHorizon] = useState(7);
  const [scenario, setScenario] = useState('baseline');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [allScenarios, setAllScenarios] = useState(null);

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.post('/predictions/create', { commodity, horizon_days: horizon, scenario });
      setResult(data);
    } catch (e) {
      setError(e.message || 'Failed to generate prediction. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCompareScenarios = async () => {
    setLoading(true);
    setError(null);
    try {
      const [base, opt, pess] = await Promise.all([
        api.post('/predictions/create', { commodity, horizon_days: horizon, scenario: 'baseline' }),
        api.post('/predictions/create', { commodity, horizon_days: horizon, scenario: 'optimistic' }),
        api.post('/predictions/create', { commodity, horizon_days: horizon, scenario: 'pessimistic' }),
      ]);
      setAllScenarios({ baseline: base, optimistic: opt, pessimistic: pess });
      setResult(base);
    } catch (e) {
      setError(e.message || 'Failed to compare scenarios.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Price Predictions</h1>
        <p className="text-muted text-sm">Generate AI-powered price forecasts with confidence scores and explanations.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 24, alignItems: 'start' }}>
        {/* Left: Prediction Form */}
        <div className="card">
          <div className="card-header"><span className="card-title">Configure Prediction</span></div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

            {/* Commodity */}
            <div className="form-group">
              <label className="form-label">Commodity</label>
              <select className="form-control" value={commodity} onChange={e => setCommodity(e.target.value)}>
                {COMMODITIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
              </select>
            </div>

            {/* Horizon */}
            <div className="form-group">
              <label className="form-label">Forecast Horizon</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {HORIZONS.map(h => (
                  <div
                    key={h.value}
                    onClick={() => setHorizon(h.value)}
                    style={{
                      padding: '10px 12px', cursor: 'pointer', borderRadius: 'var(--radius-md)',
                      border: `2px solid ${horizon === h.value ? 'var(--green-500)' : 'var(--neutral-200)'}`,
                      background: horizon === h.value ? 'var(--green-50)' : 'var(--white)',
                      transition: 'all 0.15s',
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 14, color: horizon === h.value ? 'var(--green-700)' : 'var(--neutral-700)' }}>
                      {h.label}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--neutral-500)' }}>{h.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Scenario */}
            <div className="form-group">
              <label className="form-label">Scenario</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {SCENARIOS.map(s => (
                  <div
                    key={s.value}
                    onClick={() => setScenario(s.value)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '10px 12px', cursor: 'pointer', borderRadius: 'var(--radius-md)',
                      border: `2px solid ${scenario === s.value ? s.color : 'var(--neutral-200)'}`,
                      background: scenario === s.value ? s.color + '10' : 'var(--white)',
                      transition: 'all 0.15s',
                    }}
                  >
                    <div style={{
                      width: 10, height: 10, borderRadius: '50%', background: s.color,
                      opacity: scenario === s.value ? 1 : 0.3,
                    }} />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--neutral-800)' }}>{s.label}</div>
                      <div style={{ fontSize: 11, color: 'var(--neutral-500)' }}>{s.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <button className="btn btn-primary" onClick={handlePredict} disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
              {loading ? <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, borderColor: '#ffffff55', borderTopColor: '#fff' }} /> Generating...</> : '🔮 Generate Prediction'}
            </button>

            <button className="btn btn-secondary" onClick={handleCompareScenarios} disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
              📊 Compare All Scenarios
            </button>
          </div>
        </div>

        {/* Right: Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {error && (
            <div className="alert-banner alert-critical">
              ⚠️ {error}
            </div>
          )}

          {/* Scenario comparison chart */}
          {allScenarios && (
            <div className="card">
              <div className="card-header"><span className="card-title">Scenario Comparison</span></div>
              <div className="card-body">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={[
                    { name: 'Pessimistic', price: allScenarios.pessimistic?.predicted_price, fill: 'var(--red-400)' },
                    { name: 'Baseline', price: allScenarios.baseline?.predicted_price, fill: 'var(--green-500)' },
                    { name: 'Optimistic', price: allScenarios.optimistic?.predicted_price, fill: 'var(--blue-500)' },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--neutral-200)" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${v}`} />
                    <Tooltip formatter={v => [`₹${v?.toFixed(2)}`, 'Price']} />
                    <Bar dataKey="price" radius={[4, 4, 0, 0]}>
                      {[0,1,2].map(i => <Cell key={i} fill={['var(--red-400)', 'var(--green-500)', 'var(--blue-500)'][i]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {result ? (
            <PredictionResult result={result} currentPrice={null} />
          ) : !loading && (
            <div className="card" style={{ padding: 48, textAlign: 'center' }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🔮</div>
              <div style={{ fontWeight: 600, color: 'var(--neutral-700)', marginBottom: 6 }}>No Prediction Yet</div>
              <div className="text-muted text-sm">Select a commodity and horizon, then click "Generate Prediction".</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
