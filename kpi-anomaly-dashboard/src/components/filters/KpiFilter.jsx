import { useFilters } from '../../hooks/useFilters'

const CATEGORIES = ['Revenue', 'Marketing', 'Operations', 'Customer', 'Traffic']

export default function KpiFilter() {
  const { filters, toggleArrayFilter, setFilter } = useFilters()
  const active = filters.kpiCategory
  const allActive = CATEGORIES.every(c => active.includes(c))

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-xs text-muted mr-1">Category:</span>
      <button
        className={`filter-chip text-xs ${allActive ? 'bg-gray-200 text-ink' : 'chip-inactive'}`}
        onClick={() => setFilter('kpiCategory', allActive ? [] : [...CATEGORIES])}
      >
        All
      </button>
      {CATEGORIES.map(c => {
        const isOn = active.includes(c)
        return (
          <button
            key={c}
            className="filter-chip text-xs"
            style={isOn
              ? { background: '#0078D4', color: '#fff', borderColor: '#0078D4' }
              : { background: '#F0F0F0', color: '#605E5C', borderColor: '#E0E0E0' }}
            onClick={() => toggleArrayFilter('kpiCategory', c)}
          >
            {c}
          </button>
        )
      })}
    </div>
  )
}
