const BASE_URL = 'http://localhost:8000/api';
const AUTH_URL = 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, body) {
  const token = localStorage.getItem('agri_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(
      errorData.detail || errorData.error || 'Something went wrong',
      res.status
    );
  }
  if (res.status === 204) return null;
  return res.json();
}

async function authRequest(method, path, body) {
  const token = localStorage.getItem('agri_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${AUTH_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(
      errorData.detail || errorData.error || 'Something went wrong',
      res.status
    );
  }
  return res.json();
}

export const api = {
  get:    (path)        => request('GET',    path),
  post:   (path, body)  => request('POST',   path, body),
  put:    (path, body)  => request('PUT',    path, body),
  delete: (path)        => request('DELETE', path),

  auth: {
    login: (body) => authRequest('POST', '/auth/login', body),
    createUser: (body) => authRequest('POST', '/auth/users', body),
    listUsers: ()     => authRequest('GET',  '/auth/users-list'),
    toggleUser: (id, body) => authRequest('PUT', `/auth/users/${id}/toggle`, body),
  },
};

export const COMMODITY_COLORS = {
  onion: '#8b5cf6', potato: '#f59e0b', tomato: '#ef4444', gram: '#10b981',
  tur: '#f97316', urad: '#6b7280', moong: '#84cc16', masur: '#fb923c',
};