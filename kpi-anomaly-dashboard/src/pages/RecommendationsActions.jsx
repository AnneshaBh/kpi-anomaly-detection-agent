import { useMemo } from 'react'
import { useCSVData } from '../hooks/useCSVData'
import { useFilters } from '../hooks/useFilters'
import PageShell from '../components/layout/PageShell'
import EffortMatrixScatter from '../components/charts/EffortMatrixScatter'
import ActionTable from '../components/tables/ActionTable'
import { COLORS } from '../utils/formatters'
import { countBy, buildOwnerDonutData } from '../utils/dataTransforms'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
         BarChart, Bar, XAxis, YAxis, CartesianGrid, LabelList } from 'recharts'
import { useState } from 'react'
import AnomalyDetailCard from '../components/cards/AnomalyDetailCard'

const EFFORT_OPTIONS = ['L', 'M', 'H']
const EFFORT_LABELS  = { L: 'Low', M: 'Medium', H: 'High' }

const OWNER_COLORS_MAP = {
  'Operations':        COLORS.CHART_BLUE,
  'Marketing':         COLORS.LOW,
  'Product':           COLORS.MEDIUM,
  'Exec':              COLORS.SUPPRESSED,
  'Revenue Operations + Product': COLORS.CHART_BLUE,
  'Revenue Operations + Product + Supply Chain': COLORS.HIGH,
}

function getOwnerColor(name) {
  return OWNER_COLORS_MAP[name] || COLORS.MUTED
}

export default function RecommendationsActions() {
  const { loading, error } = useCSVData()
  const { filteredFacts, filters, toggleArrayFilter, setFilter, uniqueOwners } = useFilters()
  const [selectedAnomaly, setSelectedAnomaly] = useState(null)

  const effortFiltered = useMemo(() =>
    filteredFacts.filter(f => filters.effortLevel.includes(f.effort_level)),
  [filteredFacts, filters.effortLevel])

  const ownerDonutData = useMemo(() => buildOwnerDonutData(filteredFacts), [filteredFacts])

  const llmStackData = useMemo(() => {
    const groups = {}
    filteredFacts.forEach(f => {
      const flag = f.layer4_priority_flag
      if (!groups[flag]) groups[flag] = { flag, llm: 0, playbook: 0 }
      if (f.llm_enhanced) groups[flag].llm++
      else groups[flag].playbook++
    })
    return Object.values(groups).sort((a, b) => (b.llm + b.playbook) - (a.llm + a.playbook))
  }, [filteredFacts])

  if (loading) return <div className="p-8 text-muted">Loading…</div>
  if (error)   return <div className="p-8 text-high">{error}</div>

  return (
    <PageShell
      title="Recommendations & Actions"
      subtitle="Action plan, effort matrix, and owner routing — drillthrough destination"
      slicers={
        <>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted mr-1">Effort:</span>
            {EFFORT_OPTIONS.map(e => {
              const on = filters.effortLevel.includes(e)
              return (
                <button key={e} className="filter-chip text-xs"
                  style={on
                    ? { background: COLORS[e === 'L' ? 'LOW' : e === 'H' ? 'HIGH' : 'MEDIUM'], color: '#fff',
                        borderColor: COLORS[e === 'L' ? 'LOW' : e === 'H' ? 'HIGH' : 'MEDIUM'] }
                    : { background: '#F0F0F0', color: '#605E5C', borderColor: '#E0E0E0' }}
                  onClick={() => toggleArrayFilter('effortLevel', e)}
                >{EFFORT_LABELS[e]}</button>
              )
            })}
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs text-muted mr-1">Owner:</span>
            <button
              className="filter-chip text-xs chip-inactive"
              onClick={() => setFilter('owner', [])}
            >All</button>
            {uniqueOwners.map(o => {
              const short = o.length > 20 ? o.slice(0, 18) + '…' : o
              const on = filters.owner.length === 0 || filters.owner.includes(o)
              return (
                <button key={o} className="filter-chip text-xs" title={o}
                  style={on && filters.owner.length > 0
                    ? { background: COLORS.CHART_BLUE, color: '#fff', borderColor: COLORS.CHART_BLUE }
                    : { background: '#F0F0F0', color: '#605E5C', borderColor: '#E0E0E0' }}
                  onClick={() => {
                    const cur = filters.owner
                    if (cur.includes(o)) setFilter('owner', cur.filter(x => x !== o))
                    else setFilter('owner', [...cur, o])
                  }}
                >{short}</button>
              )
            })}
          </div>
        </>
      }
    >
      {/* Section 1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <EffortMatrixScatter facts={effortFiltered} onDotClick={d => setSelectedAnomaly(d)} />

        {/* Owner Donut */}
        <div className="card" style={{ minHeight: 300 }}>
          <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
            Recommended Owner Distribution
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={ownerDonutData}
                innerRadius={55}
                outerRadius={85}
                dataKey="value"
              >
                {ownerDonutData.map(d => (
                  <Cell key={d.name} fill={getOwnerColor(d.name)} />
                ))}
              </Pie>
              <Tooltip
                formatter={(val, name) => [`${val} anomalies (${ownerDonutData.find(d => d.name === name)?.pct}%)`, name]}
                contentStyle={{ fontSize: 11, border: '1px solid #E0E0E0' }}
              />
              <Legend
                wrapperStyle={{ fontSize: 10 }}
                formatter={(value, entry) => `${value} (${entry.payload.pct}%)`}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Section 2 — LLM vs Playbook */}
      <div className="card mb-4">
        <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">
          LLM-Enhanced vs Playbook by Routing Flag
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={llmStackData} layout="vertical" margin={{ left: 100, right: 50, top: 4, bottom: 4 }}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="flag" tick={{ fontSize: 11, fill: '#605E5C' }} width={95} />
            <Tooltip contentStyle={{ fontSize: 12, border: '1px solid #E0E0E0' }} />
            <Bar dataKey="llm"      stackId="a" fill={COLORS.CHART_BLUE}  name="LLM Enhanced"  radius={[0,0,0,0]} />
            <Bar dataKey="playbook" stackId="a" fill={COLORS.SUPPRESSED}  name="Playbook Only" radius={[0,2,2,0]}>
              <LabelList dataKey="playbook" position="right" style={{ fontSize: 11, fill: '#605E5C' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted mt-2">
          MONITOR and SUPPRESSED records receive playbook text only — no LLM API call is made.
        </p>
      </div>

      {/* Section 3 — Action Table */}
      <ActionTable facts={filteredFacts} />

      {selectedAnomaly && (
        <AnomalyDetailCard anomaly={selectedAnomaly} onClose={() => setSelectedAnomaly(null)} />
      )}
    </PageShell>
  )
}
