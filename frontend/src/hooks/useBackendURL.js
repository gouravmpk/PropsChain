import { useState, useEffect } from 'react'

/**
 * useBackendURL — Fetch the backend URL from Parameter Store
 * 
 * This hook allows the frontend to work with a dynamic backend IP
 * that changes on every Fargate redeploy. Without this, we'd need
 * to rebuild the frontend every time the IP changes.
 * 
 * Flow:
 * 1. Frontend loads from CloudFront
 * 2. This hook calls `.well-known/propchain-config.json`
 * 3. That file (served by S3/CloudFront) returns the current backend URL
 * 4. API client uses this URL for all requests
 * 
 * Deploy script updates the URL in Parameter Store after each redeploy,
 * and a Lambda (or this approach) serves it to the frontend.
 */
export function useBackendURL() {
  const [backendURL, setBackendURL] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Try to fetch from config file first (for cloud deployments)
    fetch('/.well-known/propchain-config.json')
      .then(res => {
        if (!res.ok) throw new Error('Config not found')
        return res.json()
      })
      .then(data => {
        setBackendURL(data.api_url)
        setLoading(false)
      })
      .catch(err => {
        // Fallback: use environment variable (for local dev)
        const envURL = import.meta.env.VITE_API_URL
        if (envURL) {
          setBackendURL(envURL)
          setLoading(false)
        } else {
          setError(new Error('Backend URL not configured'))
          setLoading(false)
        }
      })
  }, [])

  return { backendURL, error, loading }
}

/**
 * Helper to get the API base URL
 * Usage: const apiURL = getBackendURL()
 */
export function getBackendURL() {
  return import.meta.env.VITE_API_URL || 'https://api.propchain.app'
}
