import axios from 'axios'

/**
 * API Configuration
 * 
 * PROD: Uses API Gateway endpoint from build-time environment variable
 *   - VITE_API_URL should be set to API Gateway URL at build time
 *   - API Gateway has valid AWS-managed HTTPS certificate
 *   - Proxies to Fargate backend (handles self-signed cert internally)
 * 
 * DEV: Uses Vite proxy (vite.config.js) → /api proxies to localhost:8000
 */

// Get API Gateway URL from build environment
const apiUrl = import.meta.env.VITE_API_URL || '/api'
const baseURL = apiUrl.endsWith('/api') ? apiUrl : `${apiUrl}/api`

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
