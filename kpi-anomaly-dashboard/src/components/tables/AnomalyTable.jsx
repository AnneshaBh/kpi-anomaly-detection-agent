import { useState, useMemo } from 'react'
import Papa from 'papaparse'
import AnomalyDetailCard from '../cards/AnomalyDetailCard'
import { COLORS, severityBadge, routingBadge, formatCurrency, formatPct, formatRank } from '../../utils/formatters'
import { sortBy } from '../../utils/dataTransforms'

const PAGE_SIZE = 10

export default function AnomalyTable({ facts }) {
  const [sortKey, setSortKey]   = useState('priority_rank')
  const [sortDir, setSortDir]   = useState('asc')
  const [page, setPage]         = useState(1)
  const [selected, setSelected] = useState(null)

  const sorted = useMemo(() => sortBy(facts, sortKey, sortDir), [facts, sortKey, sortDir])
  const total  = sorted.length
  const pages  = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const rows   = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  function handleSort(key) {
    if (key === sortKey) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
    setPage(1)
  }

  function exportCSV() {
    const csv = Papa.unparse(sorted.map(r => ({
      anomaly_id: r.anomaly_id, date: r.date, kpi_label: r.kpi_label,
      severity: r.severity, direction: r.direction, deviation_pct: r.deviation_pct,
      revenue_at_risk: r.revenue_at_risk, recommended_owner: r.recommended_owner,
      layer4_priority_flag: r.layer4_priority_flag, priority_rank: r.priority_rank,
    })))
    const blob = new Blob([csv], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'anomalies.csv'
    a.click()
  }

  function SortIcon({ col }) {
    if (col !== sortKey) return <span className="text-gray-300 ml-0.5">↕</span>
    return <span className="ml-0.5" style={{ color: COLORS.CHART_BLUE }}>{sortDir === 'asc' ? '↑' : '↓'}</span>
  }

  const COL = [
    { key: 'priority_rank',       label: '#',           render: r => formatRank(r.priority_rank) },
    { key: 'date',                label: 'Date',        render: r => r.date },
    { key: 'kpi_label',           label: 'KPI',         render: r => <span className="font-medium">{r.kpi_label}</span> },
    { key: 'severity',            label: 'Severity',    render: r => <span className={`chip text-xs ${severityBadge(r.severity)}`}>{r.severity}</span> },
    { key: 'direction',           label: 'Dir',         render: r => r.direction },
    { key: 'deviation_pct',       label: 'Deviation',   render: r => formatPct(r.deviation_pct) },
    { key: 'revenue_at_risk',     label: 'Rev at Risk', render: r => (
        <span style={{ color: r.revenue_at_risk > 0 ? COLORS.AT_RISK : COLORS.UPSIDE }}>
          {formatCurrency(r.revenue_at_risk)}
        </span>
      )},
    { key: 'recommended_owner',   label: 'Owner',       render: r => <span className="truncate max-w-32 block">{r.recommended_owner}</span> },
    { key: 'layer4_priority_flag',label: 'Routing',     render: r => <span className={`chip text-xs ${routingBadge(r.layer4_priority_flag)}`}>{r.layer4_priority_flag}</span> },
  ]

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-muted">{total} anomalies</span>
        <button
          onClick={exportCSV}
          className="text-xs px-3 py-1 border border-border rounded text-muted hover:bg-gray-100"
        >
          Export CSV
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {COL.map(c => (
                <th key={c.key} className="cursor-pointer select-none" onClick={() => handleSort(c.key)}>
                  {c.label}<SortIcon col={c.key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr
                key={r.anomaly_id}
                className="cursor-pointer"
                onClick={() => setSelected(r)}
              >
                {COL.map(c => (
                  <td key={c.key}>{c.render(r)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-border">
        <span className="text-xs text-muted">
          {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
        </span>
        <div className="flex gap-1">
          <button
            className="text-xs px-2 py-1 border border-border rounded disabled:opacity-40 hover:bg-gray-100"
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
          >←</button>
          {Array.from({ length: Math.min(pages, 7) }, (_, i) => i + 1).map(p => (
            <button
              key={p}
              className="text-xs px-2 py-1 border rounded"
              style={p === page
                ? { background: COLORS.CHART_BLUE, color: '#fff', borderColor: COLORS.CHART_BLUE }
                : { borderColor: '#E0E0E0' }}
              onClick={() => setPage(p)}
            >
              {p}
            </button>
          ))}
          {pages > 7 && <span className="text-xs text-muted px-1">…{pages}</span>}
          <button
            className="text-xs px-2 py-1 border border-border rounded disabled:opacity-40 hover:bg-gray-100"
            disabled={page === pages}
            onClick={() => setPage(p => p + 1)}
          >→</button>
        </div>
      </div>

      {selected && <AnomalyDetailCard anomaly={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
