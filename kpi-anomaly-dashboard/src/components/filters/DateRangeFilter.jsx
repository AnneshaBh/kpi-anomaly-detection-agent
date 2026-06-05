import { useFilters } from '../../hooks/useFilters'
import { format } from 'date-fns'

export default function DateRangeFilter() {
  const { filters, setFilter } = useFilters()
  const { dateRange } = filters

  function fmtForInput(d) {
    try { return format(new Date(d), 'yyyy-MM-dd') } catch { return '' }
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted">Date:</span>
      <input
        type="date"
        className="text-xs border border-border rounded px-2 py-1 text-ink bg-white"
        value={fmtForInput(dateRange.start)}
        onChange={e => setFilter('dateRange', { ...dateRange, start: new Date(e.target.value) })}
      />
      <span className="text-xs text-muted">–</span>
      <input
        type="date"
        className="text-xs border border-border rounded px-2 py-1 text-ink bg-white"
        value={fmtForInput(dateRange.end)}
        onChange={e => setFilter('dateRange', { ...dateRange, end: new Date(e.target.value) })}
      />
    </div>
  )
}
