import axios from 'axios'

/**
 * API Configuration Strategy:
 * 
 * DEV: Uses Vite proxy (vite.config.js) → /api proxies to localhost:8000
 * PROD: Uses backend URL from:
 *   1. .well-known/propchain-config.json (dynamic - updates without rebuild)
 *   2. VITE_API_URL env var (fallback)
 *   3. /api relative path (last resort)
 */
let baseURL = '/api' // Default: relative path

// Try to load from .well-known config (dynamic URL from Parameter Store)
if (typeof window !== 'undefined') {
  fetch('/.well-known/propchain-config.json')
    .then(res => res.ok ? res.json() : null)
    .then(data => {
      if (data?.api_url) {
        console.log('[API] Using backend URL from config:', data.api_url)
        baseURL = `${data.api_url}/api`
      }
    })
    .catch(() => {
      // Fallback to env var
      if (import.meta.env.VITE_API_URL) {
        baseURL = `${import.meta.env.VITE_API_URL}/api`
        console.log('[API] Using backend URL from env:', baseURL)
      }
    })
}

const API = axios.create({ baseURL })

API.interceptors.request.use(config => {
  const token = localStorage.getItem('propchain_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

API.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('propchain_token')
      localStorage.removeItem('propchain_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default API

export const fmt = {
  currency: (v) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', notation: 'compact', maximumFractionDigits: 2 }).format(v),
  number: (v) => new Intl.NumberFormat('en-IN').format(v),
  date: (d) => new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
  shortHash: (h) => h ? `${h.slice(0, 8)}...${h.slice(-6)}` : '-',
}
