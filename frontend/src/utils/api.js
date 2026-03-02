import axios from 'axios'

/**
 * API Configuration Strategy:
 * 
 * PROD: Uses CloudFront URL for API proxy
 *   - https://d35swpqfjmv67g.cloudfront.net/api/* proxies to backend
 *   - CloudFront handles HTTPS properly (valid cert)
 *   - Backend can use self-signed cert (trusted internally)
 *   - No cross-origin issues since same domain
 * 
 * DEV: Uses Vite proxy (vite.config.js) → /api proxies to localhost:8000
 */

// Determine if we're in production (CloudFront) or dev (local)
const isProduction = import.meta.env.PROD
const baseURL = isProduction ? '/api' : '/api'  // Both use /api, Vite/CF handle the proxy

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
