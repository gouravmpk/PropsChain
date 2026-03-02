import axios from 'axios'

/**
 * API Configuration
 * 
 * SIMPLIFIED: CloudFront routes /api/* to backend automatically
 * No need for environment variables or dynamic config
 */

const API = axios.create({ baseURL: '/api' })

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
