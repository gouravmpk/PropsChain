import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './context/AuthContext'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Properties from './pages/Properties'
import PropertyDetail from './pages/PropertyDetail'
import RegisterProperty from './pages/RegisterProperty'
import Marketplace from './pages/Marketplace'
import AIVerification from './pages/AIVerification'
import CrossVerify from './pages/CrossVerify'
import Blockchain from './pages/Blockchain'
import Transactions from './pages/Transactions'
import Portfolio from './pages/Portfolio'
import Profile from './pages/Profile'

// Shows a full-screen spinner while the stored token is being validated server-side.
// Prevents a flash of the login page for users who are already authenticated.
function AuthGate({ children }) {
  const { loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <svg className="animate-spin w-10 h-10 text-indigo-400" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-slate-400 text-sm">Verifying session…</span>
        </div>
      </div>
    )
  }
  return children
}

// Redirects unauthenticated users to /login.
function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

// Redirects already-authenticated users away from /login and /register.
function PublicOnlyRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Navigate to="/app/dashboard" replace /> : children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: '#1e1b4b', color: '#e2e8f0', border: '1px solid rgba(99,102,241,0.3)' },
            success: { iconTheme: { primary: '#10b981', secondary: '#fff' } },
            error: { iconTheme: { primary: '#ef4444', secondary: '#fff' } },
          }}
        />
        <AuthGate>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
          <Route path="/register" element={<PublicOnlyRoute><Register /></PublicOnlyRoute>} />
          <Route path="/app" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="properties" element={<Properties />} />
            <Route path="properties/:id" element={<PropertyDetail />} />
            <Route path="register-property" element={<RegisterProperty />} />
            <Route path="marketplace" element={<Marketplace />} />
            <Route path="ai-verify" element={<AIVerification />} />
            <Route path="cross-verify" element={<CrossVerify />} />
            <Route path="blockchain" element={<Blockchain />} />
            <Route path="transactions" element={<Transactions />} />
            <Route path="portfolio" element={<Portfolio />} />
            <Route path="profile" element={<Profile />} />
          </Route>
        </Routes>
        </AuthGate>
      </BrowserRouter>
    </AuthProvider>
  )
}
