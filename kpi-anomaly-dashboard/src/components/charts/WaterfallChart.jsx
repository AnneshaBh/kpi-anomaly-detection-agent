import { memo, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine, ResponsiveContainer } from 'recharts'
import { COLORS, formatCurrency } from '../../utils/formatters'
import { buildWaterfallData } from '../../utils/dataTransforms'

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="card text-xs" style={{ minWidth: 180 }}>
      <div className="font-bold text-ink">{d?.kpi_label}</div>
      <div>Revenue impact: <strong style={{ color: d?.revenue_at_risk > 0 ? COLORS.AT_RISK : COLORS.UPSIDE }}>
        {formatCurrency(d?.revenue_at_risk)}
      </strong></div>
      <div>Anomalies: {d?.count}</div>
      <div>Avg deviation: {d?.avg_deviation?.toFixed(1)}%</div>
    </div>
  )
}

function WaterfallChart({ facts, dimKpiMap }) {
  const data = useMemo(() => buildWaterfallData(facts, dimKpiMap), [facts, dimKpiMap])

  return (
    <div className="card" style={{ minHeight: 340 }}>
      <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">
        Revenue at Risk by KPI (positive = at risk, negative = captured upside)
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 60, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
          <XAxis
            dataKey="kpi_label"
            tick={{ fontSize: 10, fill: '#605E5C' }}
            angle={-35}
            textAnchor="end"
            interval={0}
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#605E5C' }}
            tickFormatter={v => formatCurrency(v, true)}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="#252423" strokeWidth={1.5} />
          <Bar dataKey="revenue_at_risk" radius={[2, 2, 0, 0]}>
            {data.map(entry => (
              <Cell
                key={entry.kpi_label}
                fill={entry.revenue_at_risk > 0 ? COLORS.AT_RISK : COLORS.UPSIDE}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(WaterfallChart)
