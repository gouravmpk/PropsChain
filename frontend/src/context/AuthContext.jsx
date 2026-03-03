import React, { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  // true while we are validating the stored token against /auth/me on first load
  const [loading, setLoading] = useState(true)

  // On mount: check if there's a stored token and validate it server-side.
  // This prevents stale / expired tokens from granting access to protected routes.
  useEffect(() => {
    const storedToken = localStorage.getItem('propchain_token')
    if (!storedToken) {
      setLoading(false)
      return
    }
    axios
      .get('/api/auth/me', { headers: { Authorization: `Bearer ${storedToken}` } })
      .then(({ data }) => {
        setToken(storedToken)
        setUser(data)
        // Refresh the cached user object in case it changed on the server
        localStorage.setItem('propchain_user', JSON.stringify(data))
      })
      .catch(() => {
        // Token is invalid or expired — wipe everything
        localStorage.removeItem('propchain_token')
        localStorage.removeItem('propchain_user')
      })
      .finally(() => setLoading(false))
  }, [])

  const login = (userData, tokenData) => {
    setUser(userData)
    setToken(tokenData)
    localStorage.setItem('propchain_user', JSON.stringify(userData))
    localStorage.setItem('propchain_token', tokenData)
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('propchain_user')
    localStorage.removeItem('propchain_token')
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading, isAuthenticated: !!user && !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
