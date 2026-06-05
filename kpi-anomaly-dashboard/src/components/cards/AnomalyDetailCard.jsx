import { useEffect } from 'react'
import { COLORS, severityBadge, routingBadge, effortBadge, formatCurrency, formatPct, formatRank, formatNumber } from '../../utils/formatters'

export default function AnomalyDetailCard({ anomaly, onClose }) {
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!anomaly) return null

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal-drawer p-0">
        {/* Header */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-border sticky top-0 bg-white z-10">
          <div>
            <div className="text-xs font-mono text-muted">{anomaly.anomaly_id}</div>
            <div className="font-bold text-ink text-base">{anomaly.kpi_label}</div>
            <div className="text-xs text-muted">{anomaly.date}</div>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-ink text-xl leading-none px-1"
          >
            ✕
          </button>
        </div>

        <div className="px-5 py-4 flex flex-col gap-4">
          {/* Badge row */}
          <div className="flex flex-wrap gap-2">
            <span className={`chip text-xs font-bold ${severityBadge(anomaly.severity)}`}>
              {anomaly.severity}
            </span>
            <span className={`chip text-xs font-bold ${routingBadge(anomaly.layer4_priority_flag)}`}>
              {anomaly.layer4_priority_flag}
            </span>
            <span className="chip text-xs border border-border text-muted">
              {anomaly.direction}
            </span>
            <span className="chip text-xs border border-border text-muted">
              {formatPct(anomaly.deviation_pct)} deviation
            </span>
          </div>

          {/* Priority */}
          <div className="card">
            <div className="text-xs text-muted mb-2 font-semibold uppercase tracking-wide">Priority</div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-lg font-bold text-ink">{formatRank(anomaly.priority_rank)}</div>
                <div className="text-xs text-muted">Rank</div>
              </div>
              <div>
                <div className="text-lg font-bold text-ink">{anomaly.priority_score?.toFixed(3)}</div>
                <div className="text-xs text-muted">Score</div>
              </div>
              <div>
                <div
                  className="text-lg font-bold"
                  style={{ color: COLORS[anomaly.priority_band] || COLORS.TEXT }}
                >
                  {anomaly.priority_band}
                </div>
                <div className="text-xs text-muted">Band</div>
              </div>
            </div>
          </div>

          {/* Revenue impact */}
          <div className="card">
            <div className="text-xs text-muted mb-2 font-semibold uppercase tracking-wide">Financial Impact</div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-muted">Revenue at Risk</div>
                <div className="font-bold" style={{ color: anomaly.revenue_at_risk > 0 ? COLORS.AT_RISK : COLORS.UPSIDE }}>
                  {formatCurrency(anomaly.revenue_at_risk)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted">Margin Impact</div>
                <div className="font-bold text-ink">{formatCurrency(anomaly.margin_impact)}</div>
              </div>
              <div>
                <div className="text-xs text-muted">Monthly Shortfall</div>
                <div className="font-bold text-ink">{formatCurrency(anomaly.monthly_shortfall)}</div>
              </div>
              <div>
                <div className="text-xs text-muted">Customers Affected</div>
                <div className="font-bold text-ink">{formatNumber(anomaly.customer_impact)}</div>
              </div>
            </div>
          </div>

          {/* RCA Narrative */}
          <div className="card">
            <div className="text-xs text-muted mb-2 font-semibold uppercase tracking-wide">Root Cause Analysis</div>
            <p className="text-sm text-ink leading-relaxed">{anomaly.rca_narrative}</p>
            {anomaly.suspected_driver_kpi && (
              <p className="text-xs text-muted mt-2">
                Suspected driver: <strong>{anomaly.suspected_driver_kpi}</strong> ({anomaly.direction})
                {anomaly.root_cause_confidence != null && ` — confidence: ${(anomaly.root_cause_confidence * 100).toFixed(0)}%`}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="card">
            <div className="text-xs text-muted mb-3 font-semibold uppercase tracking-wide">Recommended Actions</div>
            <div className="flex flex-col gap-3">
              <div>
                <div className="text-xs font-semibold text-high mb-1">Immediate Action</div>
                <p className="text-sm text-ink leading-relaxed">{anomaly.immediate_action || '—'}</p>
              </div>
              <div>
                <div className="text-xs font-semibold text-medium mb-1">Short-term Fix</div>
                <p className="text-sm text-ink leading-relaxed">{anomaly.short_term_fix || '—'}</p>
              </div>
              {anomaly.preventive_measure && (
                <div>
                  <div className="text-xs font-semibold text-low mb-1">Preventive Measure</div>
                  <p className="text-sm text-ink leading-relaxed">{anomaly.preventive_measure}</p>
                </div>
              )}
            </div>
          </div>

          {/* Meta */}
          <div className="flex flex-wrap gap-2 text-xs text-muted">
            <span>Owner: <strong className="text-ink">{anomaly.recommended_owner}</strong></span>
            <span className="text-border">|</span>
            <span className={`chip ${effortBadge(anomaly.effort_level)}`}>
              Effort: {anomaly.effort_level}
            </span>
            {anomaly.llm_enhanced && (
              <span className="chip bg-blue-50 text-blue-700 border border-blue-200">LLM Enhanced</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
