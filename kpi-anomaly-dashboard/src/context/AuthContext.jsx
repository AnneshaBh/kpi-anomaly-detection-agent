import { createContext, useCallback, useContext, useState } from 'react'

const AuthContext = createContext(null)

const USER_KEY = 'kpi_agent_user'

export function AuthProvider({ children }) {
  const [username, setUsername] = useState(() => localStorage.getItem(USER_KEY))

  const isAuthenticated = !!username

  const login = useCallback(async (user, password) => {
    const validUser = import.meta.env.VITE_AUTH_USERNAME
    const validPass = import.meta.env.VITE_AUTH_PASSWORD

    if (user === validUser && password === validPass) {
      localStorage.setItem(USER_KEY, user)
      setUsername(user)
    } else {
      throw new Error('Invalid username or password')
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(USER_KEY)
    setUsername(null)
  }, [])

  return (
    <AuthContext.Provider value={{ username, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}