import React, { createContext, useContext, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import PredictionsPage from './pages/PredictionsPage';
import RecommendationsPage from './pages/RecommendationsPage';
import CommodityDetail from './pages/CommodityDetail';
import ReportsPage from './pages/ReportsPage';
import AdminPage from './pages/AdminPage';
import LoginPage from './pages/LoginPage';
import Layout from './components/layout/Layout';
import './styles/globals.css';

// ── Auth Context ─────────────────────────────────────────────────────────────
export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('agri_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp * 1000 > Date.now()) {
          setUser({ id: payload.sub, username: payload.username, role: payload.role });
        } else {
          localStorage.removeItem('agri_token');
          setToken(null);
        }
      } catch {
        setToken(null);
      }
    }
    setLoading(false);
  }, [token]);

  const login = (tokenStr, userData) => {
    localStorage.setItem('agri_token', tokenStr);
    setToken(tokenStr);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('agri_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

function PrivateRoute({ children, requiredRole }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (requiredRole && user.role !== requiredRole && user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="predictions" element={<PredictionsPage />} />
            <Route path="recommendations" element={<RecommendationsPage />} />
            <Route path="commodities/:commodity" element={<CommodityDetail />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="admin" element={<PrivateRoute requiredRole="admin"><AdminPage /></PrivateRoute>} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}
