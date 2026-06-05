import { memo, useMemo } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, Legend, ResponsiveContainer
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { COLORS, formatCurrency } from '../../utils/formatters'

function AnomalyTimelineChart({ summaryTimeline, onBarClick }) {
  const { chartData, peakDate } = useMemo(() => {
    if (!summaryTimeline?.length) return { chartData: [], peakDate: null }
    let peak = null
    const data = summaryTimeline.map(d => {
      const row = {
        ...d,
        dateLabel: d.date ? format(parseISO(String(d.date)), "MMM ''yy") : d.date,
        dateRaw: d.date,
      }
      if (!peak || d.anomaly_count > peak.anomaly_count) peak = row
      return row
    })
    return { chartData: data, peakDate: peak }
  }, [summaryTimeline])

  function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null
    const d = payload[0]?.payload
    return (
      <div className="card text-xs" style={{ minWidth: 200 }}>
        <div className="font-bold text-ink mb-1">{d?.dateRaw}</div>
        <div>Anomaly Count: <strong>{d?.anomaly_count}</strong></div>
        <div>Escalate: {d?.escalate_count} | Investigate: {d?.investigate_count}</div>
        <div>Daily at risk: <strong style={{ color: COLORS.AT_RISK }}>{formatCurrency(d?.daily_at_risk)}</strong></div>
        <div>Daily upside: <strong style={{ color: COLORS.UPSIDE }}>{formatCurrency(Math.abs(d?.daily_upside))}</strong></div>
        <div>Cumul. upside: <strong style={{ color: COLORS.UPSIDE }}>{formatCurrency(Math.abs(d?.cumulative_upside))}</strong></div>
      </div>
    )
  }

  return (
    <div className="card" style={{ minHeight: 320 }}>
      <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">
        Daily Anomaly Count + Cumulative Upside
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 60, bottom: 0, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
          <XAxis
            dataKey="dateLabel"
            tick={{ fontSize: 10, fill: '#605E5C' }}
            interval={Math.max(0, Math.floor(chartData.length / 10) - 1)}
          />
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 10, fill: '#605E5C' }}
            label={{ value: 'Count', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#605E5C' } }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fontSize: 10, fill: COLORS.LOW }}
            tickFormatter={v => `$${(Math.abs(v) / 1000).toFixed(0)}K`}
          />
          <Tooltip content={<CustomTooltip />} />
          {peakDate && (
            <ReferenceLine
              yAxisId="left"
              x={peakDate.dateLabel}
              stroke={COLORS.HIGH}
              strokeDasharray="4 2"
              label={{ value: 'Peak', position: 'top', fontSize: 10, fill: COLORS.HIGH }}
            />
          )}
          <Bar
            yAxisId="left"
            dataKey="anomaly_count"
            fill={COLORS.CHART_BLUE}
            name="Anomaly Count"
            radius={[2, 2, 0, 0]}
            cursor="pointer"
            onClick={d => onBarClick && onBarClick(d)}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="cumulative_upside"
            stroke={COLORS.LOW}
            strokeWidth={2}
            dot={{ r: 2 }}
            name="Cumulative Upside"
          />
          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(AnomalyTimelineChart)
