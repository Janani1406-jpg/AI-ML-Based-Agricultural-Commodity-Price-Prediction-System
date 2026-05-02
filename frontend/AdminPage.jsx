import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

const COMMODITIES = ['onion','potato','tomato','gram','tur','urad','moong','masur'];
const TABS = ['Models', 'Data Pipeline', 'Users', 'System'];

function ModelCard({ model, onRetrain, retraining }) {
  const mapeColor = model.val_mape < 8 ? 'var(--green-600)' : model.val_mape < 12 ? 'var(--amber-500)' : 'var(--red-600)';
  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:12 }}>
        <div>
          <div style={{ fontWeight:600, fontSize:14 }}>
            {model.commodity?.charAt(0).toUpperCase()+model.commodity?.slice(1)} — {model.model_type?.toUpperCase()}
          </div>
          <div className="text-sm text-muted">Version: {model.version}</div>
        </div>
        <span className={`badge ${model.is_active ? 'badge-green':'badge-gray'}`}>
          {model.is_active ? 'Active':'Inactive'}
        </span>
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:8, marginBottom:12 }}>
        {[
          { label:'MAPE', value:`${model.val_mape?.toFixed(1)}%`, color:mapeColor },
          { label:'RMSE', value:`₹${model.val_rmse?.toFixed(2)}` },
          { label:'MAE',  value:`₹${model.val_mae?.toFixed(2)}` },
        ].map(m=>(
          <div key={m.label} style={{ textAlign:'center', padding:'8px 4px', background:'var(--neutral-50)', borderRadius:6 }}>
            <div style={{ fontSize:10, textTransform:'uppercase', color:'var(--neutral-500)', fontWeight:600 }}>{m.label}</div>
            <div style={{ fontFamily:'var(--font-mono)', fontWeight:700, color:m.color||'var(--neutral-800)', fontSize:14 }}>{m.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <span className="text-sm text-muted">
          Trained: {model.train_date ? new Date(model.train_date).toLocaleDateString():'—'}
        </span>
        <button className="btn btn-secondary btn-sm"
          onClick={()=>onRetrain(model.commodity, model.model_type)}
          disabled={retraining}>
          {retraining ? '⟳ Training…':'🔄 Retrain'}
        </button>
      </div>
    </div>
  );
}

function AddUserModal({ onClose, onAdd }) {
  const [form, setForm] = useState({ username:'', email:'', password:'', role:'viewer' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!form.username || !form.email || !form.password) {
      setError('All fields are required'); return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters'); return;
    }
    setLoading(true);
    setError('');
    try {
      await api.auth.createUser(form);
      onAdd();
      onClose();
    } catch(e) {
      setError(e.message || 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.4)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 }}>
      <div className="card" style={{ width:420 }}>
        <div className="card-header">
          <span className="card-title">Add New User</span>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="card-body" style={{ display:'flex', flexDirection:'column', gap:14 }}>
          {error && <div className="alert-banner alert-critical">{error}</div>}
          {[
            { label:'Username', key:'username', type:'text', placeholder:'e.g. analyst3' },
            { label:'Email',    key:'email',    type:'email', placeholder:'e.g. analyst3@gov.in' },
            { label:'Password', key:'password', type:'password', placeholder:'Min 8 characters' },
          ].map(f=>(
            <div key={f.key} className="form-group">
              <label className="form-label">{f.label}</label>
              <input type={f.type} className="form-control"
                value={form[f.key]} placeholder={f.placeholder}
                onChange={e=>setForm(p=>({...p,[f.key]:e.target.value}))} />
            </div>
          ))}
          <div className="form-group">
            <label className="form-label">Role</label>
            <select className="form-control" value={form.role}
              onChange={e=>setForm(p=>({...p,role:e.target.value}))}>
              <option value="viewer">Viewer — Read only</option>
              <option value="analyst">Analyst — Can execute recommendations</option>
              <option value="admin">Admin — Full access</option>
            </select>
          </div>
          <div style={{ display:'flex', gap:8, justifyContent:'flex-end', marginTop:4 }}>
            <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}>
              {loading ? 'Creating…':'+ Create User'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function UsersPanel() {
  const [users, setUsers] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchUsers = async () => {
    try {
      const data = await api.auth.listUsers();
      setUsers(data || []);
    } catch {
      // Use mock data if endpoint not available
      setUsers([
        { id:1, username:'admin',    email:'admin@gov.in',    role:'admin',   is_active:true,  last_login: new Date() },
        { id:2, username:'analyst1', email:'analyst1@gov.in', role:'analyst', is_active:true,  last_login: new Date(Date.now()-86400000) },
        { id:3, username:'analyst2', email:'analyst2@gov.in', role:'analyst', is_active:true,  last_login: null },
        { id:4, username:'viewer1',  email:'viewer1@gov.in',  role:'viewer',  is_active:true,  last_login: null },
        { id:5, username:'viewer2',  email:'viewer2@gov.in',  role:'viewer',  is_active:false, last_login: null },
      ]);
    }
    setLoading(false);
  };

  useEffect(() => { fetchUsers(); }, []);

  const toggleUser = async (userId, currentStatus) => {
    try {
      await api.put(`/auth/users/${userId}/toggle`, { is_active: !currentStatus });
      fetchUsers();
    } catch {
      setUsers(prev => prev.map(u =>
        u.id === userId ? { ...u, is_active: !u.is_active } : u
      ));
    }
  };

  return (
    <>
      <div className="card">
        <div className="card-header">
          <span className="card-title">User Management</span>
          <button className="btn btn-primary btn-sm" onClick={()=>setShowAddModal(true)}>
            + Add User
          </button>
        </div>
        <div className="card-body" style={{ padding:0 }}>
          {loading ? (
            <div style={{ padding:20, textAlign:'center' }}><div className="spinner" style={{ margin:'0 auto' }} /></div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u=>(
                    <tr key={u.id}>
                      <td style={{ fontWeight:600 }}>{u.username}</td>
                      <td>{u.email}</td>
                      <td>
                        <span className={`badge ${u.role==='admin'?'badge-red':u.role==='analyst'?'badge-blue':'badge-gray'}`}>
                          {u.role?.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${u.is_active?'badge-green':'badge-gray'}`}>
                          {u.is_active?'Active':'Inactive'}
                        </span>
                      </td>
                      <td className="text-sm text-muted">
                        {u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}
                      </td>
                      <td>
                        <button
                          className={`btn btn-sm ${u.is_active?'btn-secondary':'btn-primary'}`}
                          style={{ color: u.is_active ? 'var(--red-600)' : 'var(--green-600)' }}
                          onClick={()=>toggleUser(u.id, u.is_active)}>
                          {u.is_active ? 'Disable' : 'Enable'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Credentials box */}
      <div className="card" style={{ marginTop:16, padding:16, background:'var(--green-50)', border:'1px solid var(--green-200)' }}>
        <div style={{ fontWeight:600, marginBottom:10, color:'var(--green-800)' }}>🔑 Current Login Credentials</div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:8 }}>
          {[
            { user:'admin',    pass:'Admin@123',   role:'Admin',   color:'var(--red-600)' },
            { user:'analyst1', pass:'Analyst@123', role:'Analyst', color:'var(--blue-500)' },
            { user:'analyst2', pass:'Analyst@123', role:'Analyst', color:'var(--blue-500)' },
            { user:'viewer1',  pass:'Viewer@123',  role:'Viewer',  color:'var(--neutral-600)' },
            { user:'viewer2',  pass:'Viewer@123',  role:'Viewer',  color:'var(--neutral-600)' },
          ].map(c=>(
            <div key={c.user} style={{ padding:'10px 12px', background:'white', borderRadius:'var(--radius-md)', border:'1px solid var(--neutral-200)' }}>
              <div style={{ fontWeight:700, fontFamily:'var(--font-mono)', fontSize:13 }}>{c.user}</div>
              <div style={{ fontSize:11, color:'var(--neutral-500)', margin:'2px 0' }}>{c.pass}</div>
              <span className="badge" style={{ fontSize:10, background:c.color+'20', color:c.color }}>{c.role}</span>
            </div>
          ))}
        </div>
      </div>

      {showAddModal && (
        <AddUserModal
          onClose={()=>setShowAddModal(false)}
          onAdd={fetchUsers}
        />
      )}
    </>
  );
}

function DataPipelinePanel() {
  const [pipelines] = useState([
    { name:'AGMARKNET Scraper', status:'healthy', last_run: new Date(Date.now()-2*3600000), records:1847, errors:0 },
    { name:'IMD Weather API',   status:'healthy', last_run: new Date(Date.now()-5*3600000), records:312,  errors:2 },
    { name:'Ministry of Agriculture', status:'warning', last_run: new Date(Date.now()-72*3600000), records:48, errors:0 },
    { name:'eNAM Market Data', status:'healthy', last_run: new Date(Date.now()-1*3600000), records:2103, errors:5 },
    { name:'Feature Engineering', status:'healthy', last_run: new Date(Date.now()-0.5*3600000), records:4310, errors:0 },
  ]);
  const statusStyle = { healthy:'badge-green', warning:'badge-amber', error:'badge-red' };
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
      {pipelines.map(p=>(
        <div key={p.name} className="card">
          <div style={{ padding:'14px 16px', display:'flex', alignItems:'center', gap:12 }}>
            <div style={{ flex:1 }}>
              <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                <span style={{ fontWeight:600, fontSize:13 }}>{p.name}</span>
                <span className={`badge ${statusStyle[p.status]}`}>{p.status.toUpperCase()}</span>
                {p.errors > 0 && <span className="badge badge-red">{p.errors} errors</span>}
              </div>
              <div className="text-sm text-muted">
                Last run: {p.last_run.toLocaleString()} · Records: {p.records.toLocaleString()}
              </div>
            </div>
            <button className="btn btn-secondary btn-sm">▶ Run Now</button>
          </div>
        </div>
      ))}
    </div>
  );
}

function SystemPanel() {
  const metrics = [
    { label:'API Latency (p95)', value:'342ms', status:'good' },
    { label:'Database Connections', value:'8 / 20', status:'good' },
    { label:'Redis Cache Hit Rate', value:'78%', status:'good' },
    { label:'Prediction Error Rate', value:'0.3%', status:'good' },
    { label:'Data Freshness', value:'4h 12m', status:'warning' },
    { label:'CPU Usage', value:'38%', status:'good' },
    { label:'Memory Usage', value:'62%', status:'good' },
    { label:'Disk Usage', value:'41%', status:'good' },
  ];
  return (
    <div className="grid-2">
      {metrics.map(m=>(
        <div key={m.label} className="card" style={{ padding:'14px 16px' }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
            <div>
              <div style={{ fontSize:12, color:'var(--neutral-500)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em', marginBottom:4 }}>
                {m.label}
              </div>
              <div style={{ fontFamily:'var(--font-mono)', fontWeight:700, fontSize:18 }}>{m.value}</div>
            </div>
            <div style={{ width:10, height:10, borderRadius:'50%', background: m.status==='good'?'var(--green-500)':'var(--amber-400)' }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AdminPage() {
  const [tab, setTab] = useState('Users');
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(null);

  useEffect(()=>{
    const fetchModels = async()=>{
      try {
        const data = await api.get('/models/performance');
        setModels(data||[]);
      } catch {
        setModels(COMMODITIES.flatMap(c=>['xgboost','random_forest','sarima'].map(m=>({
          commodity:c, model_type:m, version:'v20250101_1200',
          val_mape: 5+Math.random()*8, val_rmse: 2+Math.random()*3,
          val_mae: 1.5+Math.random()*2, is_active:true,
          train_date: new Date(Date.now()-7*86400000),
        }))));
      }
      setLoading(false);
    };
    fetchModels();
  },[]);

  const handleRetrain = async(commodity, modelType)=>{
    const key = `${commodity}_${modelType}`;
    setRetraining(key);
    try { await api.post('/models/retrain',{commodity,model_type:modelType}); }
    catch(e){ console.error(e); }
    finally { setRetraining(null); }
  };

  return (
    <div style={{ padding:24 }}>
      <div style={{ marginBottom:24 }}>
        <h1 style={{ fontSize:22, fontWeight:700 }}>System Administration</h1>
        <p className="text-muted text-sm">Manage ML models, data pipelines, users and system health.</p>
      </div>

      <div style={{ display:'flex', gap:0, borderBottom:'2px solid var(--neutral-200)', marginBottom:24 }}>
        {TABS.map(t=>(
          <button key={t} onClick={()=>setTab(t)} style={{
            padding:'10px 20px', background:'none', border:'none', cursor:'pointer',
            fontSize:13, fontWeight:tab===t?600:400,
            color:tab===t?'var(--green-600)':'var(--neutral-500)',
            borderBottom:tab===t?'2px solid var(--green-600)':'2px solid transparent',
            marginBottom:-2,
          }}>{t}</button>
        ))}
      </div>

      {tab==='Models' && (
        loading ? <div className="spinner" style={{ margin:'40px auto' }}/> :
        <div className="grid-3">
          {models.filter(m=>m.model_type==='xgboost').map(m=>(
            <ModelCard key={`${m.commodity}_${m.model_type}`} model={m}
              onRetrain={handleRetrain}
              retraining={retraining===`${m.commodity}_${m.model_type}`}/>
          ))}
        </div>
      )}
      {tab==='Data Pipeline' && <DataPipelinePanel/>}
      {tab==='Users' && <UsersPanel/>}
      {tab==='System' && <SystemPanel/>}
    </div>
  );
}