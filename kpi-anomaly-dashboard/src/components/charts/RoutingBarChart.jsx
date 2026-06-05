import { memo, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, Cell, LabelList, Tooltip, ResponsiveContainer } from 'recharts'
import { ROUTING_COLORS } from '../../utils/formatters'

const ORDER = ['ESCALATE', 'INVESTIGATE', 'MONITOR', 'SUPPRESSED']

function RoutingBarChart({ facts, onBarClick }) {
  const data = useMemo(() => {
    const counts = {}
    facts.forEach(f => { counts[f.layer4_priority_flag] = (counts[f.layer4_priority_flag] || 0) + 1 })
    const total = facts.length
    return ORDER
      .map(name => ({
        name,
        value: counts[name] || 0,
        pct: total ? ((counts[name] || 0) / total * 100).toFixed(1) : '0',
      }))
      .filter(d => d.value > 0)
  }, [facts])

  return (
    <div className="card flex flex-col" style={{ minHeight: 280 }}>
      <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">Routing Flag Breakdown</div>
      <div className="flex-1" style={{ minHeight: 200 }}>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} layout="vertical" margin={{ left: 90, right: 50, top: 4, bottom: 4 }}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11, fill: '#605E5C' }}
              width={85}
            />
            <Tooltip
              formatter={(val, name, props) => [`${val} (${props.payload.pct}%)`, 'Count']}
              contentStyle={{ fontSize: 12, border: '1px solid #E0E0E0' }}
            />
            <Bar
              dataKey="value"
              radius={[0, 2, 2, 0]}
              onClick={d => onBarClick && onBarClick(d.name)}
              cursor="pointer"
            >
              {data.map(entry => (
                <Cell key={entry.name} fill={ROUTING_COLORS[entry.name]} />
              ))}
              <LabelList
                dataKey="value"
                position="right"
                formatter={(val, entry) => {
                  const d = data.find(d => d.value === val)
                  return d ? `${val} (${d.pct}%)` : val
                }}
                style={{ fontSize: 11, fill: '#605E5C' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default memo(RoutingBarChart)
