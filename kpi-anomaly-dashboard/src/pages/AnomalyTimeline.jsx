import { useMemo } from 'react'
import { useCSVData } from '../hooks/useCSVData'
import { useFilters } from '../hooks/useFilters'
import PageShell from '../components/layout/PageShell'
import MetricCard from '../components/cards/MetricCard'
import AnomalyTimelineChart from '../components/charts/AnomalyTimelineChart'
import CalendarHeatmap from '../components/charts/CalendarHeatmap'
import MonthlyStackedBar from '../components/charts/MonthlyStackedBar'
import { COLORS, formatCurrency } from '../utils/formatters'
import { buildMonthlyStackedData } from '../utils/dataTransforms'

const YEARS    = [2024, 2025]
const QUARTERS = ['Q1', 'Q2', 'Q3', 'Q4']

function ChipGroup({ label, options, active, onToggle, onAll }) {
  const allOn = options.every(o => active.includes(o))
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-xs text-muted mr-1">{label}:</span>
      <button
        className={`filter-chip text-xs ${allOn ? 'bg-gray-200 text-ink' : 'chip-inactive'}`}
        onClick={() => onAll(allOn ? [] : [...options])}
      >All</button>
      {options.map(o => {
        const on = active.includes(o)
        return (
          <button key={o} className="filter-chip text-xs"
            style={on
              ? { background: COLORS.CHART_BLUE, color: '#fff', borderColor: COLORS.CHART_BLUE }
              : { background: '#F0F0F0', color: '#605E5C', borderColor: '#E0E0E0' }}
            onClick={() => onToggle(o)}
          >{o}</button>
        )
      })}
    </div>
  )
}

export default function AnomalyTimeline() {
  const { data, loading, error } = useCSVData()
  const { filters, toggleArrayFilter, setFilter, filteredFacts } = useFilters()

  const filteredTimeline = useMemo(() => {
    if (!data?.summaryTimeline) return []
    const { year, quarter } = filters
    return data.summaryTimeline.filter(d => {
      if (!d.dateObj) return true
      const y = d.dateObj.getFullYear()
      const q = `Q${Math.ceil((d.dateObj.getMonth() + 1) / 3)}`
      return year.includes(y) && quarter.includes(q)
    })
  }, [data, filters])

  const metrics = useMemo(() => {
    const uniqueDates = new Set(filteredTimeline.map(d => d.date)).size
    const peakEntry = filteredTimeline.reduce((max, d) => (!max || d.anomaly_count > max.anomaly_count) ? d : max, null)
    const last = filteredTimeline[filteredTimeline.length - 1]
    const cumAtRisk = last?.cumulative_at_risk || 0
    const cumUpside = Math.abs(last?.cumulative_upside || 0)
    return { uniqueDates, peakEntry, cumAtRisk, cumUpside }
  }, [filteredTimeline])

  const monthlyData = useMemo(() => {
    if (!data) return []
    return buildMonthlyStackedData(filteredFacts, data.dimDate)
  }, [filteredFacts, data])

  if (loading) return <div className="p-8 text-muted">Loading timeline data…</div>
  if (error)   return <div className="p-8 text-high">{error}</div>

  return (
    <PageShell
      title="Anomaly Timeline"
      subtitle="Daily anomaly frequency, severity trend, and cumulative financial exposure"
      slicers={
        <>
          <ChipGroup
            label="Year"
            options={YEARS}
            active={filters.year}
            onToggle={v => toggleArrayFilter('year', v)}
            onAll={v => setFilter('year', v)}
          />
          <ChipGroup
            label="Quarter"
            options={QUARTERS}
            active={filters.quarter}
            onToggle={v => toggleArrayFilter('quarter', v)}
            onAll={v => setFilter('quarter', v)}
          />
        </>
      }
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <MetricCard label="Unique Anomaly Dates" value={metrics.uniqueDates} subtext="days with ≥1 anomaly" color={COLORS.CHART_BLUE} icon="📅" />
        <MetricCard
          label="Peak Month"
          value={metrics.peakEntry ? `${metrics.peakEntry.date?.slice(0,7)}` : '—'}
          subtext={metrics.peakEntry ? `${metrics.peakEntry.anomaly_count} anomalies` : ''}
          color={COLORS.HIGH}
          icon="📈"
        />
        <MetricCard
          label="Cumulative at Risk"
          value={formatCurrency(metrics.cumAtRisk, true)}
          subtext="cumulative exposure"
          color={COLORS.AT_RISK}
          icon="⚠️"
        />
        <MetricCard
          label="Cumulative Upside"
          value={formatCurrency(metrics.cumUpside, true)}
          subtext="captured above plan"
          color={COLORS.UPSIDE}
          icon="💚"
        />
      </div>

      {/* Timeline chart */}
      <div className="mb-4">
        <AnomalyTimelineChart summaryTimeline={filteredTimeline} />
      </div>

      {/* Calendar + Monthly bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <CalendarHeatmap summaryTimeline={data.summaryTimeline} />
        <MonthlyStackedBar data={monthlyData} />
      </div>
    </PageShell>
  )
}
