export function groupBy(arr, key) {
  return arr.reduce((acc, row) => {
    const k = row[key]
    if (!acc[k]) acc[k] = []
    acc[k].push(row)
    return acc
  }, {})
}

export function sumBy(arr, key) {
  return arr.reduce((sum, row) => sum + (Number(row[key]) || 0), 0)
}

export function avgBy(arr, key) {
  if (!arr.length) return 0
  return sumBy(arr, key) / arr.length
}

export function countBy(arr, key) {
  return arr.reduce((acc, row) => {
    const k = row[key]
    acc[k] = (acc[k] || 0) + 1
    return acc
  }, {})
}

export function uniqueValues(arr, key) {
  return [...new Set(arr.map(r => r[key]).filter(v => v != null))]
}

export function sortBy(arr, key, dir = 'asc') {
  return [...arr].sort((a, b) => {
    const av = a[key], bv = b[key]
    if (av == null) return 1
    if (bv == null) return -1
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return dir === 'asc' ? cmp : -cmp
  })
}

export function buildMonthlyStackedData(facts, dimDate) {
  const dateMap = {}
  dimDate.forEach(d => { dateMap[d.date] = d })
  const monthly = {}
  facts.forEach(f => {
    const d = dateMap[f.date]
    if (!d) return
    const ym = d.year_month
    if (!monthly[ym]) monthly[ym] = { year_month: ym, yyyymm: d.yyyymm, HIGH: 0, MEDIUM: 0, LOW: 0 }
    monthly[ym][f.severity] = (monthly[ym][f.severity] || 0) + 1
  })
  return Object.values(monthly).sort((a, b) => a.yyyymm - b.yyyymm)
}

export function buildWaterfallData(facts, dimKpiMap) {
  const kpiGroups = groupBy(facts, 'kpi')
  return Object.entries(kpiGroups)
    .map(([kpi, rows]) => {
      const label = dimKpiMap[kpi]?.kpi_label || kpi
      const total = sumBy(rows, 'revenue_at_risk')
      return { kpi_label: label, revenue_at_risk: total, count: rows.length, avg_deviation: avgBy(rows, 'deviation_pct') }
    })
    .sort((a, b) => Math.abs(b.revenue_at_risk) - Math.abs(a.revenue_at_risk))
}

export function buildKpiPriorityMatrix(facts, dimKpiMap) {
  const bands = ['HIGH', 'MEDIUM', 'LOW']
  const kpiList = [...new Set(facts.map(f => f.kpi))]
  return kpiList.map(kpi => {
    const label = dimKpiMap[kpi]?.kpi_label || kpi
    const row = { kpi, kpi_label: label }
    bands.forEach(band => {
      const subset = facts.filter(f => f.kpi === kpi && f.priority_band === band)
      row[band] = subset.length ? sumBy(subset, 'revenue_at_risk') : null
    })
    return row
  })
}

export function buildOwnerDonutData(facts) {
  const counts = countBy(facts, 'recommended_owner')
  const total = facts.length
  return Object.entries(counts).map(([name, value]) => ({
    name,
    value,
    pct: total ? ((value / total) * 100).toFixed(1) : '0',
  }))
}
