import { useCSVData } from '../../hooks/useCSVData'
import { useFilters } from '../../hooks/useFilters'
import { format } from 'date-fns'
import { COLORS } from '../../utils/formatters'

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

export default function TopBar() {
  const { data } = useCSVData()
  const { filters, resetFilters } = useFilters()

  const lastDate = data?.facts?.length
    ? data.facts.reduce((max, f) => f.date > max ? f.date : max, '')
    : null

  const { dateRange } = filters
  const startStr = dateRange?.start ? format(new Date(dateRange.start), 'MMM d, yyyy') : '—'
  const endStr   = dateRange?.end   ? format(new Date(dateRange.end),   'MMM d, yyyy') : '—'

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
        Reset all filters
      </button>
    </header>
  )
}
