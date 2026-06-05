import { memo, useMemo } from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea } from 'recharts'
import { COLORS, formatCurrency } from '../../utils/formatters'

const EFFORT_MAP = { L: 0, M: 1, H: 2 }
const EFFORT_LABELS = ['L', 'M', 'H']

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="card text-xs" style={{ minWidth: 200 }}>
      <div className="font-bold text-ink">{d?.anomaly_id}</div>
      <div className="text-muted">{d?.kpi_label}</div>
      <div className="mt-1">Effort: <strong>{d?.effort_level}</strong></div>
      <div>Revenue at risk: <strong style={{ color: d?.revenue_at_risk > 0 ? COLORS.AT_RISK : COLORS.UPSIDE }}>
        {formatCurrency(Math.abs(d?.revenue_at_risk))}
      </strong></div>
      {d?.immediate_action && (
        <div className="mt-1 text-muted" style={{ maxWidth: 200 }}>
          {d.immediate_action.slice(0, 80)}{d.immediate_action.length > 80 ? '…' : ''}
        </div>
      )}
    </div>
  )
}

function EffortMatrixScatter({ facts, onDotClick }) {
  const data = useMemo(() => {
    const risks = facts.map(f => Math.abs(f.revenue_at_risk || 0))
    const mn = Math.min(...risks)
    const mx = Math.max(...risks) || 1
    return facts
      .filter(f => f.effort_level && EFFORT_MAP[f.effort_level] !== undefined)
      .map(f => ({
        ...f,
        effortNum: EFFORT_MAP[f.effort_level],
        absRisk: Math.abs(f.revenue_at_risk || 0),
        radius: 6 + ((Math.abs(f.revenue_at_risk || 0) - mn) / (mx - mn)) * 12,
      }))
  }, [facts])

  return (
    <div className="card" style={{ minHeight: 340 }}>
      <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
        Effort vs Revenue Impact — top-left = quick wins
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 16, right: 20, bottom: 20, left: 30 }}>
          <ReferenceArea
            x1={-0.5}
            x2={0.5}
            y1={0}
            fill="#107C4115"
            label={{ value: '⚡ Quick wins', position: 'insideTopLeft', fontSize: 10, fill: COLORS.LOW, offset: 8 }}
          />
          <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
          <XAxis
            type="number"
            dataKey="effortNum"
            domain={[-0.5, 2.5]}
            ticks={[0, 1, 2]}
            tickFormatter={v => EFFORT_LABELS[v] || ''}
            label={{ value: 'Effort Level', position: 'insideBottom', offset: -10, fontSize: 10, fill: '#605E5C' }}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="absRisk"
            tick={{ fontSize: 10 }}
            tickFormatter={v => formatCurrency(v, true)}
            label={{ value: '|Revenue at Risk|', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#605E5C' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={data}
            onClick={d => onDotClick && onDotClick(d)}
            cursor="pointer"
            shape={(props) => {
              const { cx, cy, payload } = props
              return (
                <circle
                  cx={cx} cy={cy} r={payload.radius || 6}
                  fill={COLORS[payload.priority_band] || COLORS.MUTED}
                  fillOpacity={0.7}
                  stroke={COLORS[payload.priority_band] || COLORS.MUTED}
                  strokeWidth={1}
                />
              )
            }}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(EffortMatrixScatter)
