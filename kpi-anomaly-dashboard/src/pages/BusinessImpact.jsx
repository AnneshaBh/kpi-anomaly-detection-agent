import { useMemo } from 'react'
import { useCSVData } from '../hooks/useCSVData'
import { useFilters } from '../hooks/useFilters'
import PageShell from '../components/layout/PageShell'
import MetricCard from '../components/cards/MetricCard'
import KpiFilter from '../components/filters/KpiFilter'
import WaterfallChart from '../components/charts/WaterfallChart'
import { COLORS, formatCurrency, formatNumber } from '../utils/formatters'
import { sumBy, avgBy, buildKpiPriorityMatrix } from '../utils/dataTransforms'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, LabelList, ResponsiveContainer } from 'recharts'

function heatColor(val) {
  if (val == null) return 'transparent'
  if (val === 0) return '#FFFFFF'
  if (val > 0) {
    const t = Math.min(Math.abs(val) / 300000, 1)
    return `rgba(192, 0, 0, ${0.08 + t * 0.4})`
  }
  const t = Math.min(Math.abs(val) / 300000, 1)
  return `rgba(16, 124, 65, ${0.08 + t * 0.4})`
}

export default function BusinessImpact() {
  const { data, loading, error } = useCSVData()
  const { filteredFacts } = useFilters()

  const metrics = useMemo(() => {
    const customers = sumBy(filteredFacts, 'customer_impact')
    const margin    = Math.abs(sumBy(filteredFacts, 'margin_impact'))
    const avgPri    = avgBy(filteredFacts, 'priority_score')
    return { customers, margin, avgPri }
  }, [filteredFacts])

  const matrix = useMemo(() => {
    if (!data?.kpiMap) return []
    return buildKpiPriorityMatrix(filteredFacts, data.kpiMap)
  }, [filteredFacts, data])

  const impactByGroup = useMemo(() => {
    const groups = { HIGH: [], MEDIUM: [], LOW: [] }
    filteredFacts.forEach(f => {
      if (groups[f.severity]) groups[f.severity].push(f)
    })
    return ['HIGH', 'MEDIUM', 'LOW'].map(s => ({
      severity: s,
      avg_impact: avgBy(groups[s], 'impact_pct_of_plan'),
    }))
  }, [filteredFacts])

  const matrixKpis  = [...new Set(matrix.map(r => r.kpi_label))]
  const BANDS = ['HIGH', 'MEDIUM', 'LOW']

  const bandTotals = useMemo(() => {
    const t = { HIGH: 0, MEDIUM: 0, LOW: 0 }
    matrix.forEach(r => {
      BANDS.forEach(b => { if (r[b] != null) t[b] += r[b] })
    })
    return t
  }, [matrix])

  if (loading) return <div className="p-8 text-muted">Loading…</div>
  if (error)   return <div className="p-8 text-high">{error}</div>

  return (
    <PageShell
      title="Business Impact"
      subtitle="Revenue exposure, customer impact, and deviation from plan by KPI category"
      slicers={<KpiFilter />}
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        <MetricCard
          label="Customers Affected (est.)"
          value={formatNumber(metrics.customers)}
          subtext="aggregate across all anomalies"
          color={COLORS.CHART_BLUE}
          icon="👥"
        />
        <MetricCard
          label="Net Margin Benefit"
          value={formatCurrency(metrics.margin, true)}
          subtext="absolute margin impact"
          color={COLORS.UPSIDE}
          icon="📊"
        />
        <MetricCard
          label="Avg Priority Score"
          value={metrics.avgPri.toFixed(3)}
          subtext="0–1 priority signal"
          color={COLORS.MEDIUM}
          icon="🎯"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <WaterfallChart facts={filteredFacts} dimKpiMap={data?.kpiMap || {}} />

        {/* KPI × Priority Band matrix */}
        <div className="card overflow-auto" style={{ minHeight: 340 }}>
          <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">
            Revenue at Risk: KPI × Priority Band
          </div>
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                <th className="text-left pr-3">KPI</th>
                {BANDS.map(b => (
                  <th key={b} style={{ color: COLORS[b], minWidth: 90 }}>{b}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.map(row => (
                <tr key={row.kpi}>
                  <td className="font-medium pr-3 py-1.5 whitespace-nowrap">{row.kpi_label}</td>
                  {BANDS.map(b => (
                    <td key={b} className="text-center py-1.5"
                      style={{ background: heatColor(row[b]) }}>
                      {row[b] != null
                        ? <span style={{ color: row[b] > 0 ? COLORS.AT_RISK : COLORS.UPSIDE }}>
                            {formatCurrency(row[b], true)}
                          </span>
                        : <span className="text-muted">—</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-border font-bold">
                <td className="pr-3 py-1.5">Total</td>
                {BANDS.map(b => (
                  <td key={b} className="text-center py-1.5"
                    style={{ color: bandTotals[b] > 0 ? COLORS.AT_RISK : COLORS.UPSIDE }}>
                    {formatCurrency(bandTotals[b], true)}
                  </td>
                ))}
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Impact % of Plan */}
      <div className="card">
        <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-1">
          Avg Impact % of Plan by Severity
        </div>
        <p className="text-xs text-muted mb-3">
          Average % deviation from daily revenue plan across anomaly days
        </p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={impactByGroup} margin={{ top: 20, right: 20, bottom: 4, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
            <XAxis dataKey="severity" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${v.toFixed(0)}%`} />
            <Tooltip formatter={v => `${v.toFixed(1)}%`} contentStyle={{ fontSize: 12, border: '1px solid #E0E0E0' }} />
            <Bar dataKey="avg_impact" radius={[2, 2, 0, 0]}>
              {impactByGroup.map(d => <Cell key={d.severity} fill={COLORS[d.severity]} />)}
              <LabelList dataKey="avg_impact" position="top"
                formatter={v => `${v.toFixed(1)}%`}
                style={{ fontSize: 11, fill: '#605E5C' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </PageShell>
  )
}
