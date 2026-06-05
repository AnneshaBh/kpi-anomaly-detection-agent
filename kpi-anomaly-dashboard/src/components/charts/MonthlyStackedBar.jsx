import { memo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { COLORS } from '../../utils/formatters'

function MonthlyStackedBar({ data }) {
  return (
    <div className="card" style={{ minHeight: 280 }}>
      <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">
        Monthly Anomaly Count by Severity
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
          <XAxis
            dataKey="year_month"
            tick={{ fontSize: 9, fill: '#605E5C' }}
            angle={-45}
            textAnchor="end"
            interval={1}
          />
          <YAxis tick={{ fontSize: 10, fill: '#605E5C' }} />
          <Tooltip contentStyle={{ fontSize: 12, border: '1px solid #E0E0E0' }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="HIGH"   stackId="a" fill={COLORS.HIGH}   name="HIGH"   radius={[0,0,0,0]} />
          <Bar dataKey="MEDIUM" stackId="a" fill={COLORS.MEDIUM} name="MEDIUM" radius={[0,0,0,0]} />
          <Bar dataKey="LOW"    stackId="a" fill={COLORS.LOW}    name="LOW"    radius={[2,2,0,0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(MonthlyStackedBar)
