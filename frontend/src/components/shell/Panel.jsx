import React from 'react'

/**
 * Themed surface: matches ToolCard chrome (border, blur, top hairline).
 */
function Panel({ children, className = '', style, title, subtitle, id }) {
  return (
    <section
      id={id}
      style={style}
      className={`relative overflow-hidden rounded-2xl border border-stroke bg-elevated/90 shadow-card backdrop-blur-md ${className}`}
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent opacity-90"
        aria-hidden
      />
      {(title || subtitle) && (
        <div className="border-b border-stroke/80 px-4 py-3 md:px-5">
          {title && <h2 className="font-display text-lg font-semibold tracking-tight text-ink">{title}</h2>}
          {subtitle && <p className="mt-1 text-xs text-ink-muted">{subtitle}</p>}
        </div>
      )}
      <div className="p-4 md:p-5">{children}</div>
    </section>
  )
}

export default Panel
