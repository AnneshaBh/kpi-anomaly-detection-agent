export const COLORS = {
  HIGH:        '#C00000',
  MEDIUM:      '#E8A000',
  LOW:         '#107C41',
  SUPPRESSED:  '#767676',
  UPSIDE:      '#107C41',
  AT_RISK:     '#C00000',
  CHART_BLUE:  '#0078D4',
  BACKGROUND:  '#F3F2F1',
  SURFACE:     '#FFFFFF',
  BORDER:      '#E0E0E0',
  TEXT:        '#252423',
  MUTED:       '#605E5C',
}

export const ROUTING_COLORS = {
  ESCALATE:    '#C00000',
  INVESTIGATE: '#E8A000',
  MONITOR:     '#107C41',
  SUPPRESSED:  '#767676',
}

export const OWNER_COLORS = {
  Operations: '#0078D4',
  Marketing:  '#107C41',
  Product:    '#E8A000',
  Exec:       '#767676',
}

export function formatCurrency(val, compact = false) {
  if (val === null || val === undefined || isNaN(val)) return '—'
  const abs = Math.abs(val)
  const neg = val < 0
  let formatted
  if (compact && abs >= 1_000_000) {
    formatted = `$${(abs / 1_000_000).toFixed(1)}M`
  } else if (compact && abs >= 1_000) {
    formatted = `$${(abs / 1_000).toFixed(0)}K`
  } else {
    formatted = `$${Math.round(abs).toLocaleString('en-US')}`
  }
  return neg ? `−${formatted}` : formatted
}

export function formatPct(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val)) return '—'
  const sign = val >= 0 ? '+' : '−'
  return `${sign}${Math.abs(val).toFixed(decimals)}%`
}

export function formatRank(val) {
  return `#${val}`
}

export function formatNumber(val) {
  if (val === null || val === undefined || isNaN(val)) return '—'
  return Math.round(val).toLocaleString('en-US')
}

export function deviationColor(val, direction) {
  if (direction === 'UP') return val > 0 ? COLORS.LOW : COLORS.HIGH
  if (direction === 'DOWN') return val > 0 ? COLORS.HIGH : COLORS.LOW
  return COLORS.TEXT
}

export function riskColor(val) {
  return val > 0 ? COLORS.AT_RISK : COLORS.UPSIDE
}

export function severityBadge(severity) {
  const map = {
    HIGH:   'bg-red-100 text-red-800 border border-red-200',
    MEDIUM: 'bg-amber-100 text-amber-800 border border-amber-200',
    LOW:    'bg-green-100 text-green-800 border border-green-200',
  }
  return map[severity] || 'bg-gray-100 text-gray-600 border border-gray-200'
}

export function routingBadge(flag) {
  const map = {
    ESCALATE:    'bg-red-100 text-red-800 border border-red-200',
    INVESTIGATE: 'bg-amber-100 text-amber-800 border border-amber-200',
    MONITOR:     'bg-green-100 text-green-800 border border-green-200',
    SUPPRESSED:  'bg-gray-100 text-gray-600 border border-gray-200',
  }
  return map[flag] || 'bg-gray-100 text-gray-600 border border-gray-200'
}

export function effortBadge(effort) {
  const map = {
    L: 'bg-green-100 text-green-800 border border-green-200',
    M: 'bg-amber-100 text-amber-800 border border-amber-200',
    H: 'bg-red-100 text-red-800 border border-red-200',
  }
  return map[effort] || 'bg-gray-100 text-gray-600 border border-gray-200'
}

export function priorityBandColor(band) {
  return COLORS[band] || COLORS.MUTED
}

export function truncate(str, len = 120) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '…' : str
}
