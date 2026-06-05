export default function PageShell({ title, subtitle, slicers, children }) {
  return (
    <div className="flex flex-col h-full">
      {/* Slicer bar */}
      {slicers && (
        <div className="bg-white border-b border-border px-4 py-2 flex flex-wrap gap-3 items-center">
          {slicers}
        </div>
      )}

      {/* Page content */}
      <div className="flex-1 overflow-auto px-4 py-4">
        {(title || subtitle) && (
          <div className="mb-4">
            {title && <h2 className="text-base font-bold text-ink">{title}</h2>}
            {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
          </div>
        )}
        {children}
      </div>
    </div>
  )
}
