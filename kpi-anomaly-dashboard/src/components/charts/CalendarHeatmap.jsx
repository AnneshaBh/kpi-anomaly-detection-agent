import { memo, useMemo, useState } from 'react'
import { format, startOfYear, endOfYear, eachDayOfInterval, getDay, getWeek } from 'date-fns'
import { COLORS } from '../../utils/formatters'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function interpolateColor(count, max) {
  if (!count) return '#F5F5F5'
  const t = Math.min(count / Math.max(max, 1), 1)
  const r = Math.round(255 - t * (255 - 192))
  const g = Math.round(255 - t * 255)
  const b = Math.round(255 - t * 255)
  return `rgb(${r},${g},${b})`
}

function CalendarHeatmap({ summaryTimeline }) {
  const [year, setYear] = useState(2025)
  const [tooltip, setTooltip] = useState(null)

  const dateMap = useMemo(() => {
    const m = new Map()
    summaryTimeline?.forEach(d => {
      if (d.date) m.set(String(d.date), d)
    })
    return m
  }, [summaryTimeline])

  const { weeks, max } = useMemo(() => {
    const start = startOfYear(new Date(year, 0, 1))
    const end   = endOfYear(new Date(year, 0, 1))
    const days  = eachDayOfInterval({ start, end })
    let mx = 0
    const byWeek = {}
    days.forEach(d => {
      const wk  = getWeek(d, { weekStartsOn: 1 })
      const dow = (getDay(d) + 6) % 7  // Mon=0
      const key = format(d, 'yyyy-MM-dd')
      const data = dateMap.get(key)
      const count = data?.anomaly_count || 0
      if (count > mx) mx = count
      if (!byWeek[wk]) byWeek[wk] = Array(7).fill(null)
      byWeek[wk][dow] = { date: key, count, data }
    })
    return { weeks: Object.values(byWeek), max: mx }
  }, [year, dateMap])

  return (
    <div className="card" style={{ minHeight: 280 }}>
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-semibold text-muted uppercase tracking-wide">
          Anomaly Calendar Heatmap
        </div>
        <div className="flex gap-1">
          {[2024, 2025].map(y => (
            <button
              key={y}
              className="filter-chip text-xs"
              style={y === year
                ? { background: COLORS.CHART_BLUE, color: '#fff', borderColor: COLORS.CHART_BLUE }
                : { background: '#F0F0F0', color: '#605E5C', borderColor: '#E0E0E0' }}
              onClick={() => setYear(y)}
            >
              {y}
            </button>
          ))}
        </div>
      </div>

      {/* Day labels */}
      <div className="flex gap-px mb-1 ml-6">
        {DAYS.map(d => (
          <div key={d} className="text-center text-gray-400" style={{ width: 14, fontSize: 9 }}>{d[0]}</div>
        ))}
      </div>

      {/* Grid */}
      <div className="overflow-x-auto">
        <div className="flex gap-px">
          {weeks.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-px">
              {week.map((cell, di) => {
                if (!cell) return <div key={di} style={{ width: 14, height: 14 }} />
                return (
                  <div
                    key={di}
                    style={{
                      width: 14,
                      height: 14,
                      background: interpolateColor(cell.count, max),
                      borderRadius: 2,
                      cursor: cell.count ? 'pointer' : 'default',
                    }}
                    onMouseEnter={e => cell.count && setTooltip({ cell, x: e.clientX, y: e.clientY })}
                    onMouseLeave={() => setTooltip(null)}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-2">
        <span className="text-xs text-muted">Less</span>
        {[0, 0.25, 0.5, 0.75, 1].map(t => (
          <div key={t} style={{ width: 12, height: 12, background: interpolateColor(t * max, max), borderRadius: 2 }} />
        ))}
        <span className="text-xs text-muted">More</span>
      </div>

      {/* Tooltip portal */}
      {tooltip && (
        <div
          className="card text-xs shadow-lg z-50"
          style={{ position: 'fixed', left: tooltip.x + 8, top: tooltip.y - 40, pointerEvents: 'none', minWidth: 160 }}
        >
          <div className="font-bold text-ink">{tooltip.cell.date}</div>
          <div>{tooltip.cell.count} anomalies</div>
          {tooltip.cell.data && (
            <>
              <div>Escalate: {tooltip.cell.data.escalate_count}</div>
              <div>Investigate: {tooltip.cell.data.investigate_count}</div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default memo(CalendarHeatmap)
