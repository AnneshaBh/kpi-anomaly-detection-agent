import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { COLORS } from '../utils/formatters'

function GridIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 20 20" fill="none">
      <rect x="1" y="1" width="7" height="7" fill={COLORS.HIGH} rx="1" />
      <rect x="12" y="1" width="7" height="7" fill={COLORS.MEDIUM} rx="1" />
      <rect x="1" y="12" width="7" height="7" fill={COLORS.LOW} rx="1" />
      <rect x="12" y="12" width="7" height="7" fill={COLORS.CHART_BLUE} rx="1" />
    </svg>
  )
}

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const usernameRef = useRef(null)

  useEffect(() => {
    if (isAuthenticated) navigate('/overview', { replace: true })
  }, [isAuthenticated, navigate])

  useEffect(() => {
    usernameRef.current?.focus()
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/overview', { replace: true })
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: '#F3F2F1' }}
    >
      <div
        className="bg-white w-full shadow-lg"
        style={{ maxWidth: 380, borderRadius: 4, border: '1px solid #E0E0E0' }}
      >
        {/* Header */}
        <div
          className="flex items-center gap-3 px-6 py-5"
          style={{ borderBottom: '1px solid #E0E0E0' }}
        >
          <GridIcon />
          <div>
            <p className="text-xs text-muted mb-0.5 uppercase tracking-widest font-semibold">
              KPI Anomaly Detection Agent
            </p>
            <h1 className="text-base font-bold text-ink">Sign in</h1>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-muted uppercase tracking-wide">
              Username
            </label>
            <input
              ref={usernameRef}
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
              required
              className="text-sm px-3 py-2 text-ink outline-none"
              style={{
                border: '1px solid #E0E0E0',
                borderRadius: 4,
                background: '#FAFAFA',
              }}
              onFocus={e => (e.target.style.borderColor = '#0078D4')}
              onBlur={e  => (e.target.style.borderColor = '#E0E0E0')}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-muted uppercase tracking-wide">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="text-sm px-3 py-2 text-ink outline-none"
              style={{
                border: '1px solid #E0E0E0',
                borderRadius: 4,
                background: '#FAFAFA',
              }}
              onFocus={e => (e.target.style.borderColor = '#0078D4')}
              onBlur={e  => (e.target.style.borderColor = '#E0E0E0')}
            />
          </div>

          {error && (
            <p className="text-xs font-medium" style={{ color: '#C00000' }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="text-sm font-semibold text-white py-2 px-4 disabled:opacity-60"
            style={{
              background: loading ? '#605E5C' : '#0078D4',
              borderRadius: 4,
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              marginTop: 4,
            }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}