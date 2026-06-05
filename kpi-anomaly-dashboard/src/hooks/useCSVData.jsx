import { createContext, useContext, useState, useEffect, useMemo } from 'react'
import Papa from 'papaparse'
import { parseISO } from 'date-fns'

const DataContext = createContext(null)

const CSV_FILES = {
  facts:             '/data/fact_anomalies.csv',
  dimKpi:            '/data/dim_kpi.csv',
  dimDate:           '/data/dim_date.csv',
  summaryKpiImpact:  '/data/summary_kpi_impact.csv',
  summaryTimeline:   '/data/summary_timeline.csv',
}

function parseBool(val) {
  if (typeof val === 'boolean') return val
  if (typeof val === 'string') return val.toLowerCase() === 'true'
  return Boolean(val)
}

function loadCSV(path) {
  return new Promise((resolve, reject) => {
    Papa.parse(path, {
      download: true,
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (results) => resolve(results.data),
      error: (err) => reject(new Error(`Failed to load ${path}: ${err.message}`)),
    })
  })
}

export function DataProvider({ children }) {
  const [raw, setRaw] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      loadCSV(CSV_FILES.facts),
      loadCSV(CSV_FILES.dimKpi),
      loadCSV(CSV_FILES.dimDate),
      loadCSV(CSV_FILES.summaryKpiImpact),
      loadCSV(CSV_FILES.summaryTimeline),
    ])
      .then(([rawFacts, dimKpi, dimDate, summaryKpiImpact, summaryTimeline]) => {
        const kpiMap = {}
        dimKpi.forEach(k => { kpiMap[k.kpi] = k })

        const facts = rawFacts.map(f => ({
          ...f,
          is_externally_driven: parseBool(f.is_externally_driven),
          escalation_suppressed: parseBool(f.escalation_suppressed),
          llm_enhanced: parseBool(f.llm_enhanced),
          dateObj: f.date ? parseISO(String(f.date)) : null,
          kpi_label:    kpiMap[f.kpi]?.kpi_label    || f.kpi,
          kpi_category: kpiMap[f.kpi]?.kpi_category || 'Other',
          kpi_tier:     kpiMap[f.kpi]?.tier         || f.tier,
          preventive_measure: f.preventive_measure || null,
        }))

        const parsedDimDate = dimDate.map(d => ({
          ...d,
          dateObj: d.date ? parseISO(String(d.date)) : null,
        }))

        const parsedTimeline = summaryTimeline.map(d => ({
          ...d,
          dateObj: d.date ? parseISO(String(d.date)) : null,
        }))

        setRaw({ facts, dimKpi, kpiMap, dimDate: parsedDimDate, summaryKpiImpact, summaryTimeline: parsedTimeline })
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <DataContext.Provider value={{ data: raw, loading, error }}>
      {children}
    </DataContext.Provider>
  )
}

export function useCSVData() {
  const ctx = useContext(DataContext)
  if (!ctx) throw new Error('useCSVData must be used inside DataProvider')
  return ctx
}
