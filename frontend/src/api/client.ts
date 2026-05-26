const getApiBase = (): string => {
  const filePreviewBase =
    window.location.protocol === 'file:' ? 'http://5.78.135.11:8000/api/v1' : '/api/v1';
  // @ts-ignore
  const configured = window.__VEKLOM_API_BASE__ || filePreviewBase;
  const base = String(configured).replace(/\/+$/, '');
  // Ensure we include '/api/v1' in base path if not present (unless it is root API base)
  if (!base.includes('/api/v1') && !base.startsWith('http') && base !== '') {
    return `${base}/api/v1`;
  }
  return base;
};

const BASE = getApiBase();
let token = localStorage.getItem('veklom_token') || '';

export const setToken = (t: string) => {
  token = t;
  if (t) {
    localStorage.setItem('veklom_token', t);
  } else {
    localStorage.removeItem('veklom_token');
  }
};

export const getToken = () => token;

export const api = async (path: string, options: RequestInit = {}) => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(token ? { Authorization: token.startsWith('Bearer ') ? token : `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${BASE}${cleanPath}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errMessage = `Request failed with status ${response.status}`;
    try {
      const err = await response.json();
      errMessage = err.detail || err.message || errMessage;
    } catch (_) {
      // ignore parsing failure
    }
    throw new Error(errMessage);
  }

  // Handle empty or void responses (e.g. DELETE or status code 204)
  if (response.status === 204) {
    return null;
  }

  return response.json();
};