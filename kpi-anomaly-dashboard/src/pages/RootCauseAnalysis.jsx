import { useMemo, useState } from 'react'
import { useCSVData } from '../hooks/useCSVData'
import { useFilters } from '../hooks/useFilters'
import PageShell from '../components/layout/PageShell'
import MetricCard from '../components/cards/MetricCard'
import ScatterConfidence from '../components/charts/ScatterConfidence'
import AnomalyDetailCard from '../components/cards/AnomalyDetailCard'
import { COLORS, formatPct } from '../utils/formatters'
import { avgBy, countBy } from '../utils/dataTransforms'
import {
  BarChart, Bar, XAxis, YAxis, Cell, Tooltip, LabelList, ResponsiveContainer
} from 'recharts'

const CONFIDENCE_TIERS = ['HIGH', 'MEDIUM', 'LOW']

function ChipGroup({ label, options, active, onToggle, onAll }) {
  const allOn = options.every(o => active.includes(o))
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-muted mr-1">{label}:</span>
      <button className={`filter-chip text-xs ${allOn ? 'bg-gray-200 text-ink' : 'chip-inactive'}`}
        onClick={() => onAll(allOn ? [] : [...options])}>All</button>
      {options.map(o => {
        const on = active.includes(o)
        return (
          <button key={o} className="filter-chip text-xs"
            style={on
              ? { background: COLORS[o] || COLORS.CHART_BLUE, color: '#fff', borderColor: COLORS[o] || COLORS.CHART_BLUE }
              : { background: '#F0F0F0', color: '#605E5C', borderColor: '#E0E0E0' }}
            onClick={() => onToggle(o)}
          >{o}</button>
        )
      })}
    </div>
  )
}

export default function RootCauseAnalysis() {
  const { loading, error } = useCSVData()
  const { filteredFacts } = useFilters()
  const [confTiers, setConfTiers] = useState([...CONFIDENCE_TIERS])
  const [extDriven, setExtDriven] = useState('both')
  const [selectedAnomaly, setSelectedAnomaly] = useState(null)

  const filtered = useMemo(() => {
    return filteredFacts.filter(f => {
      if (f.confidence_tier && !confTiers.includes(f.confidence_tier)) return false
      if (extDriven === 'true'  && !f.is_externally_driven) return false
      if (extDriven === 'false' && f.is_externally_driven)  return false
      return true
    })
  }, [filteredFacts, confTiers, extDriven])

  const metrics = useMemo(() => {
    const total = filteredFacts.length || 1
    const escalate  = filteredFacts.filter(f => f.severity === 'HIGH').length
    const llmEnhanced = filteredFacts.filter(f => f.llm_enhanced).length
    const extDrivenCount = filteredFacts.filter(f => f.is_externally_driven).length
    const highConf = filteredFacts.filter(f => f.severity === 'HIGH' && f.root_cause_confidence != null)
    const avgConf = highConf.length ? avgBy(highConf, 'root_cause_confidence') : 0
    return {
      escalationRate: (escalate / total * 100).toFixed(1),
      llmPct: (llmEnhanced / total * 100).toFixed(1),
      extPct: (extDrivenCount / total * 100).toFixed(1),
      avgConf: (avgConf * 100).toFixed(0),
    }
  }, [filteredFacts])

  const externalDriverData = useMemo(() => {
    const ext = filteredFacts.filter(f => f.is_externally_driven && f.external_driver_type && f.external_driver_type !== 'none')
    const counts = countBy(ext, 'external_driver_type')
    const total = ext.length || 1
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value, pct: (value / total * 100).toFixed(1) }))
      .sort((a, b) => b.value - a.value)
  }, [filteredFacts])

  const externallyDrivenFacts = useMemo(() =>
    filteredFacts.filter(f => f.is_externally_driven), [filteredFacts])

  const [expanded, setExpanded] = useState(null)

  if (loading) return <div className="p-8 text-muted">Loading…</div>
  if (error)   return <div className="p-8 text-high">{error}</div>

  return (
    <PageShell
      title="Root Cause Analysis"
      subtitle="Causal confidence, external drivers, and actionability quadrant"
      slicers={
        <>
          <ChipGroup
            label="Confidence Tier"
            options={CONFIDENCE_TIERS}
            active={confTiers}
            onToggle={v => setConfTiers(p => p.includes(v) ? p.filter(x => x !== v) : [...p, v])}
            onAll={v => setConfTiers(v)}
          />
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted mr-1">External:</span>
            {['both', 'true', 'false'].map(v => (
              <button key={v} className="filter-chip text-xs"
                style={extDriven === v
                  ? { background: COLORS.CHART_BLUE, color: '#fff', borderColor: COLORS.CHART_BLUE }
                  : { background: '#F0F0F0', color: '#605E5C', borderColor: '#E0E0E0' }}
                onClick={() => setExtDriven(v)}
              >{v === 'both' ? 'All' : v === 'true' ? 'External' : 'Internal'}</button>
            ))}
          </div>
        </>
      }
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <MetricCard label="Escalation Rate"        value={`${metrics.escalationRate}%`} subtext="HIGH severity / total" color={COLORS.HIGH} icon="🚨" />
        <MetricCard label="LLM-Enhanced Recs"      value={`${metrics.llmPct}%`}         subtext="LLM-generated actions"  color={COLORS.CHART_BLUE} icon="🤖" />
        <MetricCard label="Externally Driven"      value={`${metrics.extPct}%`}         subtext="external factor events" color={COLORS.MEDIUM} icon="🌐" />
        <MetricCard label="Avg Causal Confidence"  value={`${metrics.avgConf}%`}         subtext="HIGH severity only"     color={COLORS.LOW} icon="🎯" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        {/* External driver bar */}
        <div className="card" style={{ minHeight: 300 }}>
          <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">
            External Driver Types
          </div>
          {externalDriverData.length ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={externalDriverData} layout="vertical" margin={{ left: 140, right: 60, top: 4, bottom: 4 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#605E5C' }} width={135} />
                <Tooltip
                  formatter={(val, _, props) => [`${val} (${props.payload.pct}%)`, 'Count']}
                  contentStyle={{ fontSize: 12, border: '1px solid #E0E0E0' }}
                />
                <Bar dataKey="value" radius={[0, 2, 2, 0]}>
                  {externalDriverData.map(d => (
                    <Cell key={d.name}
                      fill={d.name === 'competitive_pressure' ? COLORS.HIGH : COLORS.MEDIUM} />
                  ))}
                  <LabelList dataKey="value" position="right"
                    formatter={v => {
                      const d = externalDriverData.find(x => x.value === v)
                      return d ? `${v} (${d.pct}%)` : v
                    }}
                    style={{ fontSize: 11, fill: '#605E5C' }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="text-sm text-muted">No external driver data in selection</div>}
          <p className="text-xs text-muted mt-2">
            competitive_pressure events are suppressed — no alert sent
          </p>
        </div>

        {/* Scatter */}
        <ScatterConfidence facts={filtered} onDotClick={d => setSelectedAnomaly(d)} />
      </div>

      {/* Externally driven table */}
      <div className="card overflow-hidden">
        <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">
          Externally Driven Anomalies ({externallyDrivenFacts.length})
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th>Date</th><th>KPI</th><th>External Driver</th><th>Direction</th>
                <th>Suppressed</th><th>RCA Narrative</th>
              </tr>
            </thead>
            <tbody>
              {externallyDrivenFacts.map(r => (
                <>
                  <tr key={r.anomaly_id} className="cursor-pointer" onClick={() => setExpanded(e => e === r.anomaly_id ? null : r.anomaly_id)}>
                    <td>{r.date}</td>
                    <td className="font-medium">{r.kpi_label}</td>
                    <td>{r.external_driver_type}</td>
                    <td>{r.direction}</td>
                    <td>
                      {r.escalation_suppressed
                        ? <span className="chip text-xs bg-gray-100 text-gray-600 border border-gray-200">Suppressed</span>
                        : <span className="chip text-xs bg-green-100 text-green-800 border border-green-200">Sent</span>}
                    </td>
                    <td className="text-xs text-muted max-w-xs">
                      {expanded === r.anomaly_id
                        ? r.rca_narrative
                        : <>{r.rca_narrative?.slice(0, 120)}{r.rca_narrative?.length > 120 && <button className="text-pbi ml-1" onClick={e => { e.stopPropagation(); setExpanded(r.anomaly_id) }}>…read more</button>}</>}
                    </td>
                  </tr>
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedAnomaly && (
        <AnomalyDetailCard anomaly={selectedAnomaly} onClose={() => setSelectedAnomaly(null)} />
      )}
    </PageShell>
  )
}
