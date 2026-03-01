import axios from 'axios'

// In dev: Vite proxies /api → localhost:8000 (see vite.config.js)
// In prod: VITE_API_URL=https://propchain-api.onrender.com (set on Vercel)
const baseURL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

const API = axios.create({ baseURL })

API.interceptors.request.use(config => {
  const token = localStorage.getItem('propchain_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default API

export const fmt = {
  currency: (v) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', notation: 'compact', maximumFractionDigits: 2 }).format(v),
  number: (v) => new Intl.NumberFormat('en-IN').format(v),
  date: (d) => new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
  shortHash: (h) => h ? `${h.slice(0, 8)}...${h.slice(-6)}` : '-',
}
