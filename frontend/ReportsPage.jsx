import React, { useState } from 'react';
import { api } from '../utils/api';

const REPORT_TYPES = [
  { value: 'weekly_summary',   label: 'Weekly Summary',   desc: 'Price trends and alerts for the past week',          icon: '📅' },
  { value: 'monthly_analysis', label: 'Monthly Analysis', desc: 'Detailed monthly price analysis with forecasts',      icon: '📆' },
  { value: 'annual_review',    label: 'Annual Review',    desc: 'Year-over-year comparison and seasonal patterns',     icon: '📊' },
  { value: 'custom',           label: 'Custom Report',    desc: 'Select your own date range and parameters',           icon: '⚙️' },
];

const COMMODITIES = ['onion','potato','tomato','gram','tur','urad','moong','masur'];

export default function ReportsPage() {
  const [reportType, setReportType]     = useState('weekly_summary');
  const [format, setFormat]             = useState('pdf');
  const [commodities, setCommodities]   = useState([]);
  const [startDate, setStartDate]       = useState('');
  const [endDate, setEndDate]           = useState('');
  const [includeCharts, setIncludeCharts] = useState(true);
  const [includeRecs, setIncludeRecs]   = useState(true);
  const [generating, setGenerating]     = useState(false);
  const [progress, setProgress]         = useState(0);
  const [lastReport, setLastReport]     = useState(null);
  const [error, setError]               = useState('');

  const toggleCommodity = (c) =>
    setCommodities(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]);

  const handleGenerate = async () => {
    setGenerating(true);
    setProgress(0);
    setError('');
    setLastReport(null);

    const interval = setInterval(() => setProgress(p => Math.min(p + 15, 90)), 400);

    try {
      const payload = {
        report_type: reportType,
        format,
        commodities: commodities.length > 0 ? commodities : null,
        start_date: startDate || null,
        end_date: endDate || null,
        include_charts: includeCharts,
        include_recommendations: includeRecs,
      };

      const data = await api.post('/reports/generate', payload);
      setProgress(100);

      if (data?.download_url) {
        // Auto download the file
        const token = localStorage.getItem('agri_token');
        const res = await fetch(`http://localhost:8000${data.download_url}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error('Download failed');

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        setLastReport({
          filename: data.filename,
          url: data.download_url,
          generatedAt: new Date().toLocaleString(),
        });
      }
    } catch (e) {
      setError(e.message || 'Failed to generate report. Please try again.');
    } finally {
      clearInterval(interval);
      setGenerating(false);
      setTimeout(() => setProgress(0), 2000);
    }
  };

  const handleRedownload = async () => {
    if (!lastReport) return;
    try {
      const token = localStorage.getItem('agri_token');
      const res = await fetch(`http://localhost:8000${lastReport.url}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = lastReport.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      setError('Re-download failed. Please generate a new report.');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Report Generation</h1>
        <p className="text-muted text-sm">
          Generate PDF or Excel reports for Ministry records and stakeholder presentations.
        </p>
      </div>

      {error && (
        <div className="alert-banner alert-critical" style={{ marginBottom: 16 }}>
          ⚠️ {error}
          <button onClick={() => setError('')}
            style={{ background:'none', border:'none', cursor:'pointer', marginLeft:8, color:'inherit' }}>✕</button>
        </div>
      )}

      {lastReport && (
        <div className="alert-banner alert-low" style={{ marginBottom: 16 }}>
          ✅ Report generated: <strong>{lastReport.filename}</strong> · {lastReport.generatedAt}
          <button className="btn btn-secondary btn-sm" onClick={handleRedownload}
            style={{ marginLeft: 12 }}>
            ⬇️ Download Again
          </button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: 24, alignItems: 'start' }}>

        {/* ── Left: Config Panel ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Report Type */}
          <div className="card">
            <div className="card-header"><span className="card-title">Report Type</span></div>
            <div className="card-body" style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {REPORT_TYPES.map(rt => (
                <div key={rt.value} onClick={() => setReportType(rt.value)} style={{
                  display:'flex', gap:10, padding:'12px 14px', cursor:'pointer',
                  borderRadius:'var(--radius-md)',
                  border:`2px solid ${reportType === rt.value ? 'var(--green-500)' : 'var(--neutral-200)'}`,
                  background: reportType === rt.value ? 'var(--green-50)' : 'var(--white)',
                  transition:'all 0.15s',
                }}>
                  <span style={{ fontSize:22, flexShrink:0 }}>{rt.icon}</span>
                  <div>
                    <div style={{ fontWeight:600, fontSize:13,
                      color: reportType === rt.value ? 'var(--green-800)' : 'var(--neutral-800)' }}>
                      {rt.label}
                    </div>
                    <div style={{ fontSize:11, color:'var(--neutral-500)', marginTop:2 }}>{rt.desc}</div>
                  </div>
                  {reportType === rt.value && (
                    <div style={{ marginLeft:'auto', color:'var(--green-600)', fontWeight:700 }}>✓</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Options */}
          <div className="card">
            <div className="card-header"><span className="card-title">Options</span></div>
            <div className="card-body" style={{ display:'flex', flexDirection:'column', gap:14 }}>

              {/* Format */}
              <div className="form-group">
                <label className="form-label">Output Format</label>
                <div style={{ display:'flex', gap:8 }}>
                  {[
                    { value:'pdf',   label:'📄 PDF',   desc:'Professional document' },
                    { value:'excel', label:'📊 Excel', desc:'Data spreadsheet' },
                  ].map(f => (
                    <div key={f.value} onClick={() => setFormat(f.value)} style={{
                      flex:1, padding:'10px 12px', cursor:'pointer', textAlign:'center',
                      borderRadius:'var(--radius-md)',
                      border:`2px solid ${format === f.value ? 'var(--green-500)' : 'var(--neutral-200)'}`,
                      background: format === f.value ? 'var(--green-50)' : 'var(--white)',
                      transition:'all 0.15s',
                    }}>
                      <div style={{ fontWeight:600, fontSize:14 }}>{f.label}</div>
                      <div style={{ fontSize:10, color:'var(--neutral-500)', marginTop:2 }}>{f.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Custom date range */}
              {reportType === 'custom' && (
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
                  <div className="form-group">
                    <label className="form-label">Start Date</label>
                    <input type="date" className="form-control"
                      value={startDate} onChange={e => setStartDate(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">End Date</label>
                    <input type="date" className="form-control"
                      value={endDate} onChange={e => setEndDate(e.target.value)} />
                  </div>
                </div>
              )}

              {/* Commodities */}
              <div>
                <label className="form-label" style={{ display:'block', marginBottom:8 }}>
                  Commodities <span style={{ color:'var(--neutral-400)', fontWeight:400 }}>(all if none selected)</span>
                </label>
                <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                  {COMMODITIES.map(c => (
                    <span key={c} onClick={() => toggleCommodity(c)} style={{
                      padding:'5px 12px', borderRadius:20, cursor:'pointer',
                      fontSize:12, fontWeight:600,
                      background: commodities.includes(c) ? 'var(--green-600)' : 'var(--neutral-200)',
                      color: commodities.includes(c) ? '#fff' : 'var(--neutral-600)',
                      transition:'all 0.15s',
                      userSelect:'none',
                    }}>
                      {c.charAt(0).toUpperCase() + c.slice(1)}
                    </span>
                  ))}
                </div>
                {commodities.length > 0 && (
                  <button onClick={() => setCommodities([])}
                    style={{ background:'none', border:'none', cursor:'pointer',
                      color:'var(--neutral-500)', fontSize:11, marginTop:6 }}>
                    ✕ Clear selection
                  </button>
                )}
              </div>

              {/* Checkboxes */}
              {[
                { key:'charts', label:'Include Charts & Visualizations', val:includeCharts, set:setIncludeCharts },
                { key:'recs',   label:'Include Buffer Stock Recommendations', val:includeRecs, set:setIncludeRecs },
              ].map(opt => (
                <label key={opt.key} style={{ display:'flex', alignItems:'center', gap:10, cursor:'pointer', padding:'4px 0' }}>
                  <input type="checkbox" checked={opt.val}
                    onChange={e => opt.set(e.target.checked)}
                    style={{ width:16, height:16, accentColor:'var(--green-600)', cursor:'pointer' }} />
                  <span style={{ fontSize:13, color:'var(--neutral-700)' }}>{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Generate Button */}
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}
            style={{ justifyContent:'center', padding:'13px 0', fontSize:15, borderRadius:'var(--radius-md)' }}>
            {generating
              ? <><span className="spinner" style={{ width:16, height:16, borderWidth:2, borderColor:'#ffffff55', borderTopColor:'#fff', marginRight:8 }} />
                  Generating {format.toUpperCase()}...
                </>
              : `📥 Generate ${format.toUpperCase()} Report`
            }
          </button>

          {/* Progress bar */}
          {progress > 0 && (
            <div>
              <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
                <span className="text-sm text-muted">
                  {progress < 100 ? 'Generating report...' : '✅ Report ready!'}
                </span>
                <span className="text-sm" style={{ fontWeight:600 }}>{progress}%</span>
              </div>
              <div className="confidence-bar confidence-high">
                <div className="confidence-fill" style={{ width:`${progress}%`, transition:'width 0.3s ease' }} />
              </div>
            </div>
          )}
        </div>

        {/* ── Right: Preview Panel ── */}
        <div className="card" style={{ minHeight:500 }}>
          <div className="card-header"><span className="card-title">Report Preview</span></div>
          <div style={{ padding:32 }}>
            {/* Report preview info */}
            <div style={{ textAlign:'center', marginBottom:32 }}>
              <div style={{ fontSize:64, marginBottom:12 }}>
                {REPORT_TYPES.find(r => r.value === reportType)?.icon}
              </div>
              <div style={{ fontWeight:700, fontSize:18, color:'var(--neutral-800)', marginBottom:6 }}>
                {REPORT_TYPES.find(r => r.value === reportType)?.label}
              </div>
              <div style={{ fontSize:13, color:'var(--neutral-500)', maxWidth:320, margin:'0 auto' }}>
                {format === 'pdf'
                  ? 'A professional PDF document with tables and styling'
                  : 'An Excel workbook with multiple data sheets'}
              </div>
            </div>

            {/* What the report includes */}
            <div style={{
              padding:20, background:'var(--neutral-50)',
              borderRadius:'var(--radius-lg)', marginBottom:20,
            }}>
              <div style={{ fontWeight:700, fontSize:13, marginBottom:12, color:'var(--neutral-800)' }}>
                📋 Report will include:
              </div>
              {[
                { icon:'💰', text:'Current prices for all selected commodities' },
                { icon:'📈', text:'Price trend analysis and historical comparison' },
                { icon:'🔮', text:'AI predictions (7, 15, 30, 90 days)' },
                includeRecs ? { icon:'📋', text:'Buffer stock recommendations with risk levels' } : null,
                includeCharts ? { icon:'📊', text:'Charts and data visualizations' } : null,
                format === 'excel' ? { icon:'📑', text:'Multiple data sheets (Prices, Predictions, Markets, Stats)' } : null,
                { icon:'🔐', text:'Officially formatted for Ministry of Consumer Affairs' },
              ].filter(Boolean).map((item, i) => (
                <div key={i} style={{
                  display:'flex', alignItems:'center', gap:10,
                  fontSize:13, color:'var(--neutral-700)',
                  padding:'6px 0',
                  borderBottom: i < 5 ? '1px solid var(--neutral-200)' : 'none',
                }}>
                  <span style={{ fontSize:16 }}>{item.icon}</span>
                  <span>{item.text}</span>
                </div>
              ))}
            </div>

            {/* Report details */}
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
              {[
                { label:'Format', value: format.toUpperCase() },
                { label:'Period',
                  value: reportType === 'weekly_summary'   ? 'Last 7 days'
                       : reportType === 'monthly_analysis' ? 'Last 30 days'
                       : reportType === 'annual_review'    ? 'Last 365 days'
                       : `${startDate || 'Custom'} → ${endDate || 'Today'}` },
                { label:'Commodities', value: commodities.length > 0 ? commodities.length + ' selected' : 'All 8' },
                { label:'Language', value: 'English' },
              ].map(item => (
                <div key={item.label} style={{
                  padding:'10px 12px', background:'var(--white)',
                  border:'1px solid var(--neutral-200)',
                  borderRadius:'var(--radius-md)',
                }}>
                  <div style={{ fontSize:10, color:'var(--neutral-500)', textTransform:'uppercase',
                    fontWeight:600, letterSpacing:'0.04em', marginBottom:3 }}>
                    {item.label}
                  </div>
                  <div style={{ fontWeight:700, fontSize:13 }}>{item.value}</div>
                </div>
              ))}
            </div>

            {/* Instructions */}
            <div style={{
              marginTop:20, padding:'12px 14px',
              background:'var(--blue-100)', borderRadius:'var(--radius-md)',
              fontSize:12, color:'var(--neutral-700)',
            }}>
              💡 <strong>How it works:</strong> Click "Generate Report" → the file will automatically
              download to your Downloads folder. For PDF, open with any PDF reader.
              For Excel, open with Microsoft Excel or Google Sheets.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}