import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../../context/AuthContext'

export default function LoginModal({ onClose }) {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const usernameRef = useRef(null)

  // Auto-focus username field and close on Escape
  useEffect(() => {
    usernameRef.current?.focus()
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      onClose()
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.45)' }}
      onClick={onClose}
    >
      <div
        className="bg-white w-full max-w-sm shadow-xl"
        style={{ borderRadius: 4, border: '1px solid #E0E0E0' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: '1px solid #E0E0E0' }}
        >
          <div>
            <p className="text-xs text-muted mb-0.5">KPI Anomaly Detection Agent</p>
            <h2 className="text-sm font-bold text-ink">Sign in</h2>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-ink text-lg leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-5 py-5 flex flex-col gap-4">
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
            }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
