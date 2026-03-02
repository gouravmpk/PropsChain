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

let configPromise = null // Cache the config fetch promise to avoid refetching

// Function to load config and return the resolved baseURL
async function loadConfig() {
  // Return cached promise if already fetching
  if (configPromise) return configPromise

  configPromise = (async () => {
    let baseURL = '/api' // Default: relative path

    try {
      const res = await fetch('/.well-known/propchain-config.json', { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json()
        if (data?.api_url) {
          baseURL = `${data.api_url}/api`
          console.log('[API] Using backend URL from config:', baseURL)
          return baseURL
        }
      }
    } catch (err) {
      console.warn('[API] Config fetch failed:', err.message)
    }

    // Fallback to env var
    if (import.meta.env.VITE_API_URL) {
      baseURL = `${import.meta.env.VITE_API_URL}/api`
      console.log('[API] Using backend URL from env:', baseURL)
      return baseURL
    }

    console.log('[API] Using relative path:', baseURL)
    return baseURL
  })()

  return configPromise
}

// Create axios instance immediately with default baseURL
const API = axios.create({ baseURL: '/api' })

// Request interceptor: Wait for config to load, verify we're using correct baseURL
API.interceptors.request.use(async (config) => {
  // Add auth token
  const token = localStorage.getItem('propchain_token')
  if (token) config.headers.Authorization = `Bearer ${token}`

  // If baseURL is still default, update it from config
  if (config.baseURL === '/api') {
    const resolvedURL = await loadConfig()
    config.baseURL = resolvedURL
    // Also update the instance defaults for subsequent requests
    if (API.defaults.baseURL === '/api' && resolvedURL !== '/api') {
      API.defaults.baseURL = resolvedURL
      console.log('[API] Updated axios defaults to use:', resolvedURL)
    }
  }

  return config
})

// Response interceptor: Handle 401 by clearing auth and redirecting
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
