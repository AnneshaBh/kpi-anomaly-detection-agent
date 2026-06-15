import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY = 'kpi_agent_token'
const USER_KEY  = 'kpi_agent_user'

export function AuthProvider({ children }) {
  const [token, setToken]       = useState(() => localStorage.getItem(TOKEN_KEY))
  const [username, setUsername] = useState(() => localStorage.getItem(USER_KEY))
  const [checking, setChecking] = useState(true)

  // On mount, verify the stored token is still valid
  useEffect(() => {
    if (!token) {
      setChecking(false)
      return
    }
    fetch('/api/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        if (!r.ok) throw new Error('expired')
        return r.json()
      })
      .then(data => setUsername(data.username))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        setToken(null)
        setUsername(null)
      })
      .finally(() => setChecking(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async (user, password) => {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail ?? 'Login failed')
    }
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(USER_KEY, data.username)
    setToken(data.token)
    setUsername(data.username)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUsername(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, username, isAuthenticated: !!token, login, logout, checking }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
