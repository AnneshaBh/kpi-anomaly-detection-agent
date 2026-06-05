import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFilters } from '../hooks/useFilters'
import PageShell from '../components/layout/PageShell'
import MetricCard from '../components/cards/MetricCard'
import SeverityFilter from '../components/filters/SeverityFilter'
import DateRangeFilter from '../components/filters/DateRangeFilter'
import PriorityDonut from '../components/charts/PriorityDonut'
import RoutingBarChart from '../components/charts/RoutingBarChart'
import AnomalyTable from '../components/tables/AnomalyTable'
import { useCSVData } from '../hooks/useCSVData'
import { COLORS, formatCurrency } from '../utils/formatters'
import { sumBy } from '../utils/dataTransforms'

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="grid grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-20" />)}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="skeleton h-72" />
        <div className="skeleton h-72" />
      </div>
      <div className="skeleton h-64" />
    </div>
  )
}

export default function ExecutiveOverview() {
  const { loading, error } = useCSVData()
  const { filteredFacts, setFilter } = useFilters()
  const navigate = useNavigate()

  const metrics = useMemo(() => {
    const total   = filteredFacts.length
    const highPri = filteredFacts.filter(f => f.severity === 'HIGH').length
    const atRisk  = sumBy(filteredFacts.filter(f => f.revenue_at_risk > 0), 'revenue_at_risk')
    const upside  = Math.abs(sumBy(filteredFacts.filter(f => f.revenue_at_risk < 0), 'revenue_at_risk'))
    const dates   = new Set(filteredFacts.map(f => f.date)).size
    return { total, highPri, atRisk, upside, dates }
  }, [filteredFacts])

  function handleDonutClick(band) {
    setFilter('priorityBand', [band])
    navigate('/recommendations')
  }

  function handleRoutingClick(flag) {
    setFilter('routingFlag', [flag])
    navigate('/recommendations')
  }

  if (loading) return <LoadingSkeleton />
  if (error) return (
    <div className="p-8 text-center">
      <div className="text-high font-bold mb-2">Data Load Error</div>
      <div className="text-sm text-muted">{error}</div>
    </div>
  )

  return (
    <PageShell
      title="Executive Overview"
      subtitle="Anomaly summary across all KPIs — filter by severity and date range"
      slicers={<><SeverityFilter /><DateRangeFilter /></>}
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <MetricCard
          label="Total Anomalies Detected"
          value={metrics.total}
          subtext={`across ${metrics.dates} unique dates`}
          color={COLORS.CHART_BLUE}
          icon="📊"
        />
        <MetricCard
          label="High Priority"
          value={metrics.highPri}
          subtext="HIGH severity anomalies"
          color={COLORS.HIGH}
          icon="🚨"
        />
        <MetricCard
          label="Revenue at Risk"
          value={formatCurrency(metrics.atRisk, true)}
          subtext="positive deviation from plan"
          color={COLORS.AT_RISK}
          icon="⚠️"
        />
        <MetricCard
          label="Captured Upside"
          value={formatCurrency(metrics.upside, true)}
          subtext="revenue above forecast"
          color={COLORS.UPSIDE}
          icon="📈"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <PriorityDonut facts={filteredFacts} onSliceClick={handleDonutClick} />
        <RoutingBarChart facts={filteredFacts} onBarClick={handleRoutingClick} />
      </div>

      {/* Table */}
      <AnomalyTable facts={filteredFacts} />
    </PageShell>
  )
}
