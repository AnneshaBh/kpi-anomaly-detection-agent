import { useEffect, useRef, useState } from 'react'

function useCountUp(target, duration = 300) {
  const [display, setDisplay] = useState(target)
  const prev = useRef(target)

  useEffect(() => {
    if (typeof target !== 'number') { setDisplay(target); return }
    const start = prev.current ?? 0
    const diff  = target - start
    if (diff === 0) return
    const startTime = performance.now()
    function tick(now) {
      const elapsed = now - startTime
      const pct     = Math.min(elapsed / duration, 1)
      setDisplay(Math.round(start + diff * pct))
      if (pct < 1) requestAnimationFrame(tick)
      else { prev.current = target }
    }
    requestAnimationFrame(tick)
  }, [target, duration])

  return display
}

export default function MetricCard({ label, value, subtext, color, icon }) {
  const isNum = typeof value === 'number'
  const animated = useCountUp(isNum ? value : 0)
  const display = isNum ? animated : value

  return (
    <div
      className="metric-card flex flex-col gap-1"
      style={{ borderLeftColor: color || '#E0E0E0' }}
    >
      <div className="flex items-center gap-1.5">
        {icon && <span className="text-sm">{icon}</span>}
        <span className="text-xs text-muted font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className="text-xl font-bold text-ink leading-tight" style={{ color: color || '#252423' }}>
        {display}
      </div>
      {subtext && (
        <div className="text-xs text-muted">{subtext}</div>
      )}
    </div>
  )
}
