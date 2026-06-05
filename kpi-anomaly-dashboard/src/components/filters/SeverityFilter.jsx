import { useFilters } from '../../hooks/useFilters'
import { COLORS } from '../../utils/formatters'

const SEVERITIES = ['HIGH', 'MEDIUM', 'LOW']

export default function SeverityFilter() {
  const { filters, toggleArrayFilter, setFilter } = useFilters()
  const active = filters.severity

  const allActive = SEVERITIES.every(s => active.includes(s))

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-muted mr-1">Severity:</span>
      <button
        className={`filter-chip text-xs ${allActive ? 'bg-gray-200 text-ink' : 'chip-inactive'}`}
        onClick={() => setFilter('severity', allActive ? [] : [...SEVERITIES])}
      >
        All
      </button>
      {SEVERITIES.map(s => {
        const isOn = active.includes(s)
        return (
          <button
            key={s}
            className="filter-chip text-xs font-bold"
            style={isOn
              ? { background: COLORS[s], color: '#fff', borderColor: COLORS[s] }
              : { background: '#F0F0F0', color: '#605E5C', borderColor: '#E0E0E0' }}
            onClick={() => toggleArrayFilter('severity', s)}
          >
            {s}
          </button>
        )
      })}
    </div>
  )
}
