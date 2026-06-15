import { useEffect, useRef, useState } from 'react'
import { useCSVData } from '../../hooks/useCSVData'
import { useFilters } from '../../hooks/useFilters'
import { useAuth } from '../../context/AuthContext'
import { format } from 'date-fns'
import { COLORS } from '../../utils/formatters'
import LoginModal from '../auth/LoginModal'

function GridIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="1" y="1" width="7" height="7" fill={COLORS.HIGH} rx="1"/>
      <rect x="12" y="1" width="7" height="7" fill={COLORS.MEDIUM} rx="1"/>
      <rect x="1" y="12" width="7" height="7" fill={COLORS.LOW} rx="1"/>
      <rect x="12" y="12" width="7" height="7" fill={COLORS.CHART_BLUE} rx="1"/>
    </svg>
  )
}

const STATUS_COLOR = { running: COLORS.MUTED, done: COLORS.LOW, error: COLORS.HIGH }

export default function TopBar() {
  const { data, refresh }        = useCSVData()
  const { filters, resetFilters } = useFilters()
  const { isAuthenticated, username, logout, token } = useAuth()

  const [showLogin, setShowLogin]         = useState(false)
  const [pipelineState, setPipelineState] = useState('idle')   // idle | running | done | error
  const [pipelineStep, setPipelineStep]   = useState(null)
  const [pipelineError, setPipelineError] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => () => clearInterval(pollRef.current), [])

  const lastDate = data?.facts?.length
    ? data.facts.reduce((max, f) => f.date > max ? f.date : max, '')
    : null

  const { dateRange } = filters
  const startStr = dateRange?.start ? format(new Date(dateRange.start), 'MMM d, yyyy') : '—'
  const endStr   = dateRange?.end   ? format(new Date(dateRange.end),   'MMM d, yyyy') : '—'

  async function handleRefresh() {
    if (pipelineState === 'running') return
    setPipelineState('running')
    setPipelineStep(null)
    setPipelineError(null)

    try {
      const res = await fetch('/api/run-pipeline', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? 'Failed to start pipeline')
      }

      // Poll status every 2 s until done or error
      pollRef.current = setInterval(async () => {
        try {
          const sr     = await fetch('/api/pipeline-status', { headers: { Authorization: `Bearer ${token}` } })
          const status = await sr.json()
          setPipelineStep(status.step)

          if (status.state === 'done') {
            clearInterval(pollRef.current)
            setPipelineState('done')
            refresh()
            setTimeout(() => setPipelineState('idle'), 4000)
          } else if (status.state === 'error') {
            clearInterval(pollRef.current)
            setPipelineState('error')
            setPipelineError(status.error)
          }
        } catch {
          clearInterval(pollRef.current)
          setPipelineState('error')
          setPipelineError('Lost connection to API server')
        }
      }, 2000)
    } catch (err) {
      setPipelineState('error')
      setPipelineError(err.message)
    }
  }

  const statusLabel =
    pipelineState === 'running' ? (pipelineStep ?? 'Starting…')
    : pipelineState === 'done'  ? 'Done'
    : pipelineState === 'error' ? `Error${pipelineError ? ` — ${pipelineError.slice(0, 55)}` : ''}`
    : null

  return (
    <header className="flex items-center gap-3 px-4 bg-white border-b border-border" style={{ height: 52, minHeight: 52 }}>
      <GridIcon />
      <h1 className="text-sm font-bold text-ink whitespace-nowrap">KPI Anomaly Detection Agent</h1>

      <div className="h-4 w-px bg-border mx-1" />

      <span className="text-xs text-muted hidden md:block">
        {startStr} – {endStr}
      </span>

      <div className="flex-1" />

      {lastDate && (
        <span className="text-xs text-muted hidden lg:block">
          Last refresh: <strong>{lastDate}</strong>
        </span>
      )}

      <button
        onClick={resetFilters}
        className="text-xs px-3 py-1 rounded border border-border text-muted hover:bg-gray-100 hover:text-ink transition-all"
      >
        Reset filters
      </button>

      {isAuthenticated ? (
        <>
          {statusLabel && (
            <span
              className="text-xs font-medium hidden md:block max-w-xs truncate"
              style={{ color: STATUS_COLOR[pipelineState] }}
              title={pipelineError ?? undefined}
            >
              {statusLabel}
            </span>
          )}

          <button
            onClick={handleRefresh}
            disabled={pipelineState === 'running'}
            className="text-xs px-3 py-1 font-semibold text-white disabled:opacity-60 whitespace-nowrap"
            style={{
              background: pipelineState === 'running' ? COLORS.MUTED : COLORS.CHART_BLUE,
              borderRadius: 4,
              border: 'none',
              cursor: pipelineState === 'running' ? 'not-allowed' : 'pointer',
            }}
          >
            {pipelineState === 'running' ? 'Running…' : 'Refresh Pipeline'}
          </button>

          <div className="h-4 w-px bg-border" />

          <span className="text-xs text-muted hidden sm:block">{username}</span>
          <button
            onClick={logout}
            className="text-xs px-2 py-1 rounded border border-border text-muted hover:bg-gray-100 hover:text-ink transition-all whitespace-nowrap"
          >
            Sign out
          </button>
        </>
      ) : (
        <button
          onClick={() => setShowLogin(true)}
          className="text-xs px-3 py-1 font-semibold text-white whitespace-nowrap"
          style={{ background: COLORS.CHART_BLUE, borderRadius: 4, border: 'none', cursor: 'pointer' }}
        >
          Sign in
        </button>
      )}

      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}
    </header>
  )
}
