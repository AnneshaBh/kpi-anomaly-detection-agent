import { useState, useMemo } from 'react'
import Papa from 'papaparse'
import { severityBadge, effortBadge, formatCurrency } from '../../utils/formatters'
import { sortBy } from '../../utils/dataTransforms'
import { COLORS } from '../../utils/formatters'

const PAGE_SIZE = 15

export default function ActionTable({ facts }) {
  const [sortKeys, setSortKeys]   = useState([{ key: 'priority_rank', dir: 'asc' }])
  const [page, setPage]           = useState(1)
  const [search, setSearch]       = useState('')
  const [expanded, setExpanded]   = useState(null)

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return q
      ? facts.filter(f =>
          (f.anomaly_id || '').toLowerCase().includes(q) ||
          (f.kpi_label  || '').toLowerCase().includes(q) ||
          (f.kpi        || '').toLowerCase().includes(q) ||
          (f.immediate_action || '').toLowerCase().includes(q) ||
          (f.rca_narrative    || '').toLowerCase().includes(q))
      : facts
  }, [facts, search])

  const sorted = useMemo(() => {
    if (!sortKeys.length) return filtered
    return [...filtered].sort((a, b) => {
      for (const { key, dir } of sortKeys) {
        const av = a[key], bv = b[key]
        if (av == null) return 1
        if (bv == null) return -1
        const cmp = av < bv ? -1 : av > bv ? 1 : 0
        if (cmp !== 0) return dir === 'asc' ? cmp : -cmp
      }
      return 0
    })
  }, [filtered, sortKeys])

  const total = sorted.length
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const rows  = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  function handleSort(key, shiftKey) {
    setSortKeys(prev => {
      const existing = prev.find(s => s.key === key)
      if (shiftKey) {
        if (existing) return prev.map(s => s.key === key ? { ...s, dir: s.dir === 'asc' ? 'desc' : 'asc' } : s)
        return [...prev, { key, dir: 'asc' }]
      }
      if (existing && prev.length === 1) return [{ key, dir: existing.dir === 'asc' ? 'desc' : 'asc' }]
      return [{ key, dir: 'asc' }]
    })
    setPage(1)
  }

  function SortIcon({ col }) {
    const s = sortKeys.find(sk => sk.key === col)
    if (!s) return <span className="text-gray-300 ml-0.5">↕</span>
    const idx = sortKeys.indexOf(s)
    return <span className="ml-0.5" style={{ color: COLORS.CHART_BLUE }}>{s.dir === 'asc' ? '↑' : '↓'}{sortKeys.length > 1 ? idx + 1 : ''}</span>
  }

  function exportCSV() {
    const csv = Papa.unparse(sorted)
    const blob = new Blob([csv], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'action_plan.csv'
    a.click()
  }

  const COLS = [
    { key: 'anomaly_id',         label: 'ID',          render: r => <span className="font-mono text-xs text-muted">{r.anomaly_id}</span> },
    { key: 'date',               label: 'Date',        render: r => r.date },
    { key: 'kpi_label',          label: 'KPI',         render: r => <span className="font-medium">{r.kpi_label}</span> },
    { key: 'priority_band',      label: 'Priority',    render: r => <span className={`chip text-xs ${severityBadge(r.priority_band)}`}>{r.priority_band}</span> },
    { key: 'effort_level',       label: 'Effort',      render: r => <span className={`chip text-xs ${effortBadge(r.effort_level)}`}>{r.effort_level}</span> },
    { key: 'immediate_action',   label: 'Immediate',   render: r => <span className="text-xs">{r.immediate_action?.slice(0, 80)}{r.immediate_action?.length > 80 ? '…' : ''}</span> },
    { key: 'short_term_fix',     label: 'Short-term',  render: r => <span className="text-xs">{r.short_term_fix?.slice(0, 60)}{r.short_term_fix?.length > 60 ? '…' : ''}</span> },
    { key: 'recommended_owner',  label: 'Owner',       render: r => <span className="text-xs">{r.recommended_owner}</span> },
    { key: 'revenue_at_risk',    label: 'Rev Impact',  render: r => <span style={{ color: r.revenue_at_risk > 0 ? COLORS.AT_RISK : COLORS.UPSIDE, fontSize: 12 }}>{formatCurrency(r.revenue_at_risk)}</span> },
  ]

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <input
          type="text"
          placeholder="Search anomaly ID, KPI, action…"
          className="text-xs border border-border rounded px-3 py-1.5 text-ink flex-1 max-w-xs"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
        />
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">{total} rows</span>
          <button
            onClick={exportCSV}
            className="text-xs px-3 py-1.5 border border-border rounded text-muted hover:bg-gray-100"
          >
            Export CSV
          </button>
        </div>
      </div>
      <p className="text-xs text-muted mb-2">Click column header to sort; Shift+click to add secondary sort. Click row to expand.</p>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse" style={{ minWidth: 900 }}>
          <thead>
            <tr>
              {COLS.map(c => (
                <th
                  key={c.key}
                  className="cursor-pointer select-none"
                  onClick={e => handleSort(c.key, e.shiftKey)}
                >
                  {c.label}<SortIcon col={c.key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <>
                <tr
                  key={r.anomaly_id}
                  className="cursor-pointer"
                  onClick={() => setExpanded(e => e === r.anomaly_id ? null : r.anomaly_id)}
                  style={expanded === r.anomaly_id ? { background: '#F0F7FF' } : {}}
                >
                  {COLS.map(c => (
                    <td key={c.key}>{c.render(r)}</td>
                  ))}
                </tr>
                {expanded === r.anomaly_id && (
                  <tr key={`${r.anomaly_id}-exp`}>
                    <td colSpan={COLS.length} style={{ padding: '12px 16px', background: '#F8F9FA', borderBottom: '2px solid #E0E0E0' }}>
                      <div className="grid grid-cols-1 gap-3 text-sm">
                        <div>
                          <span className="text-xs font-semibold text-muted uppercase">RCA Narrative</span>
                          <p className="text-ink mt-1 leading-relaxed">{r.rca_narrative}</p>
                        </div>
                        {r.preventive_measure && (
                          <div>
                            <span className="text-xs font-semibold text-muted uppercase">Preventive Measure</span>
                            <p className="text-ink mt-1 leading-relaxed">{r.preventive_measure}</p>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
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
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
            className="text-xs px-2 py-1 border border-border rounded disabled:opacity-40 hover:bg-gray-100">←</button>
          {Array.from({ length: Math.min(pages, 7) }, (_, i) => i + 1).map(p => (
            <button key={p} onClick={() => setPage(p)}
              className="text-xs px-2 py-1 border rounded"
              style={p === page
                ? { background: COLORS.CHART_BLUE, color: '#fff', borderColor: COLORS.CHART_BLUE }
                : { borderColor: '#E0E0E0' }}>
              {p}
            </button>
          ))}
          {pages > 7 && <span className="text-xs text-muted px-1">…{pages}</span>}
          <button disabled={page === pages} onClick={() => setPage(p => p + 1)}
            className="text-xs px-2 py-1 border border-border rounded disabled:opacity-40 hover:bg-gray-100">→</button>
        </div>
      </div>
    </div>
  )
}
