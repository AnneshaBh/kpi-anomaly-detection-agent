import { memo, useMemo } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, ZAxis
} from 'recharts'
import { COLORS, formatCurrency } from '../../utils/formatters'

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="card text-xs" style={{ minWidth: 200 }}>
      <div className="font-bold text-ink">{d?.anomaly_id}</div>
      <div className="text-muted">{d?.date} · {d?.kpi_label}</div>
      <div className="mt-1">Confidence: <strong>{(d?.root_cause_confidence * 100)?.toFixed(0)}%</strong></div>
      <div>Actionability: <strong>{(d?.actionability_score * 100)?.toFixed(0)}%</strong></div>
      <div>Revenue: <strong style={{ color: d?.revenue_at_risk > 0 ? COLORS.AT_RISK : COLORS.UPSIDE }}>
        {formatCurrency(d?.revenue_at_risk)}
      </strong></div>
    </div>
  )
}

function ScatterConfidence({ facts, onDotClick }) {
  const { data, rMin, rMax } = useMemo(() => {
    const filtered = facts.filter(f => f.root_cause_confidence != null && f.actionability_score != null)
    const risks = filtered.map(f => Math.abs(f.revenue_at_risk || 0))
    const mn = Math.min(...risks)
    const mx = Math.max(...risks)
    return { data: filtered, rMin: mn, rMax: mx }
  }, [facts])

  function normRadius(r) {
    const span = rMax - rMin || 1
    return 6 + ((Math.abs(r) - rMin) / span) * 14
  }

  const QUADRANT_LABELS = [
    { x: 0.75, y: 0.85, text: 'Act immediately', color: COLORS.HIGH },
    { x: 0.15, y: 0.85, text: 'Investigate further', color: COLORS.MEDIUM },
    { x: 0.75, y: 0.15, text: 'Limited actionability', color: COLORS.MUTED },
    { x: 0.15, y: 0.15, text: 'Monitor', color: COLORS.LOW },
  ]

  return (
    <div className="card" style={{ minHeight: 340 }}>
      <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
        Confidence vs Actionability (bubble = |revenue at risk|)
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 16, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
          <XAxis
            type="number"
            dataKey="root_cause_confidence"
            domain={[0, 1]}
            tick={{ fontSize: 10 }}
            label={{ value: 'Causal Confidence', position: 'insideBottom', offset: -10, fontSize: 10, fill: '#605E5C' }}
          />
          <YAxis
            type="number"
            dataKey="actionability_score"
            domain={[0, 1]}
            tick={{ fontSize: 10 }}
            label={{ value: 'Actionability', angle: -90, position: 'insideLeft', offset: 10, fontSize: 10, fill: '#605E5C' }}
          />
          <ZAxis range={[36, 400]} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine x={0.5} stroke="#E0E0E0" strokeDasharray="4 2" />
          <ReferenceLine y={0.5} stroke="#E0E0E0" strokeDasharray="4 2" />
          <Scatter
            data={data}
            onClick={d => onDotClick && onDotClick(d)}
            cursor="pointer"
            shape={(props) => {
              const { cx, cy, payload } = props
              const r = normRadius(payload.revenue_at_risk || 0)
              return (
                <circle
                  cx={cx} cy={cy} r={r}
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
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1 text-xs text-muted">
        <span>↗ High conf + High action: <strong>act immediately</strong></span>
        <span>↖ Low conf + High action: <strong>investigate</strong></span>
        <span>↘ High conf + Low action: <strong>monitor closely</strong></span>
        <span>↙ Low conf + Low action: <strong>monitor</strong></span>
      </div>
    </div>
  )
}

export default memo(ScatterConfidence)
