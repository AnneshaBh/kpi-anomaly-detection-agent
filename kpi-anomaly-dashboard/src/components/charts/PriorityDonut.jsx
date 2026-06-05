import { memo, useMemo } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { COLORS } from '../../utils/formatters'

function PriorityDonut({ facts, onSliceClick }) {
  const data = useMemo(() => {
    const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 }
    facts.forEach(f => { if (counts[f.priority_band] !== undefined) counts[f.priority_band]++ })
    const total = facts.length
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value, pct: total ? ((value / total) * 100).toFixed(1) : '0' }))
      .filter(d => d.value > 0)
  }, [facts])

  const total = facts.length

  return (
    <div className="card flex flex-col" style={{ minHeight: 280 }}>
      <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Priority Distribution</div>
      <div className="flex-1 flex items-center justify-center" style={{ minHeight: 200 }}>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={data}
              innerRadius={55}
              outerRadius={80}
              dataKey="value"
              onClick={d => onSliceClick && onSliceClick(d.name)}
              cursor="pointer"
            >
              {data.map(entry => (
                <Cell key={entry.name} fill={COLORS[entry.name]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(val, name) => [`${val} anomalies`, name]}
              contentStyle={{ fontSize: 12, border: '1px solid #E0E0E0' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Center label overlay — approximate positioning */}
      <div className="text-center -mt-24 mb-16">
        <div className="text-2xl font-bold text-ink">{total}</div>
        <div className="text-xs text-muted">total</div>
      </div>

      {/* Legend */}
      <div className="flex justify-center gap-4 mt-2">
        {data.map(d => (
          <button
            key={d.name}
            className="flex items-center gap-1.5 text-xs cursor-pointer hover:opacity-70"
            onClick={() => onSliceClick && onSliceClick(d.name)}
          >
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: COLORS[d.name] }} />
            <span className="text-ink font-medium">{d.name}</span>
            <span className="text-muted">{d.value} ({d.pct}%)</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export default memo(PriorityDonut)
