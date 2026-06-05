import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import { COLORS } from '../../utils/formatters'

const NAV = [
  { path: '/overview',        label: 'Executive Overview',        icon: '📊' },
  { path: '/timeline',        label: 'Anomaly Timeline',          icon: '📅' },
  { path: '/root-cause',      label: 'Root Cause Analysis',       icon: '🔍' },
  { path: '/impact',          label: 'Business Impact',           icon: '💰' },
  { path: '/recommendations', label: 'Recommendations & Actions', icon: '✅' },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className="flex flex-col bg-white border-r border-border transition-all duration-200"
      style={{ width: collapsed ? 52 : 220, minWidth: collapsed ? 52 : 220 }}
    >
      {/* Logo row */}
      <div className="flex items-center gap-2 px-3 py-3 border-b border-border" style={{ minHeight: 52 }}>
        {!collapsed && (
          <span className="text-xs font-bold text-muted uppercase tracking-widest truncate">
            Anomaly Agent
          </span>
        )}
        <button
          onClick={() => setCollapsed(c => !c)}
          className="ml-auto p-1 rounded hover:bg-gray-100 text-muted"
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-2">
        {NAV.map(({ path, label, icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 mx-1 rounded text-sm font-medium transition-all duration-150 cursor-pointer no-underline
               ${isActive
                 ? 'bg-red-50 text-high font-semibold'
                 : 'text-ink hover:bg-gray-100'}`
            }
            style={({ isActive }) => isActive
              ? { borderLeft: `3px solid ${COLORS.HIGH}`, paddingLeft: 9 }
              : { borderLeft: '3px solid transparent', paddingLeft: 9 }}
          >
            <span className="text-base leading-none">{icon}</span>
            {!collapsed && (
              <span className="truncate leading-tight">{label}</span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border px-3 py-2">
        {!collapsed && (
          <p className="text-xs text-muted">KPI Anomaly Detection</p>
        )}
      </div>
    </aside>
  )
}
