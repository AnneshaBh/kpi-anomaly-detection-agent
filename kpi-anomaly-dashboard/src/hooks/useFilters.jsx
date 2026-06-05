import { createContext, useContext, useState, useMemo } from 'react'
import { useCSVData } from './useCSVData'
import { parseISO, isWithinInterval } from 'date-fns'

const FilterContext = createContext(null)

const defaultFilters = {
  severity:    ['HIGH', 'MEDIUM', 'LOW'],
  direction:   ['UP', 'DOWN'],
  routingFlag: ['ESCALATE', 'INVESTIGATE', 'MONITOR', 'SUPPRESSED'],
  priorityBand:['HIGH', 'MEDIUM', 'LOW'],
  kpiCategory: ['Revenue', 'Marketing', 'Operations', 'Customer', 'Traffic'],
  effortLevel: ['L', 'M', 'H'],
  owner:       [],            // populated from data
  dateRange:   { start: new Date('2024-01-01'), end: new Date('2025-12-31') },
  year:        [2024, 2025],
  quarter:     ['Q1', 'Q2', 'Q3', 'Q4'],
}

export function FilterProvider({ children }) {
  const { data } = useCSVData()
  const [filters, setFilters] = useState(defaultFilters)

  const uniqueOwners = useMemo(() => {
    if (!data?.facts) return []
    return [...new Set(data.facts.map(f => f.recommended_owner).filter(Boolean))]
  }, [data])

  const activeFilters = useMemo(() => {
    const owner = filters.owner.length ? filters.owner : uniqueOwners
    return { ...filters, owner }
  }, [filters, uniqueOwners])

  const filteredFacts = useMemo(() => {
    if (!data?.facts) return []
    const { severity, direction, routingFlag, priorityBand, kpiCategory,
            effortLevel, owner, dateRange } = activeFilters
    return data.facts.filter(f => {
      if (!severity.includes(f.severity)) return false
      if (!direction.includes(f.direction)) return false
      if (!routingFlag.includes(f.layer4_priority_flag)) return false
      if (!priorityBand.includes(f.priority_band)) return false
      if (!kpiCategory.includes(f.kpi_category)) return false
      if (!effortLevel.includes(f.effort_level)) return false
      if (owner.length && !owner.includes(f.recommended_owner)) return false
      if (f.dateObj) {
        const start = dateRange.start instanceof Date ? dateRange.start : parseISO(dateRange.start)
        const end   = dateRange.end   instanceof Date ? dateRange.end   : parseISO(dateRange.end)
        if (!isWithinInterval(f.dateObj, { start, end })) return false
      }
      return true
    })
  }, [data, activeFilters])

  function setFilter(key, val) {
    setFilters(prev => ({ ...prev, [key]: val }))
  }

  function resetFilters() {
    setFilters(defaultFilters)
  }

  function toggleArrayFilter(key, val) {
    setFilters(prev => {
      const arr = prev[key]
      return {
        ...prev,
        [key]: arr.includes(val) ? arr.filter(v => v !== val) : [...arr, val],
      }
    })
  }

  return (
    <FilterContext.Provider value={{
      filters: activeFilters,
      setFilter,
      resetFilters,
      toggleArrayFilter,
      filteredFacts,
      uniqueOwners,
    }}>
      {children}
    </FilterContext.Provider>
  )
}

export function useFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error('useFilters must be used inside FilterProvider')
  return ctx
}
