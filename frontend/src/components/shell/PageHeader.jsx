import React from 'react'

/**
 * Shared page title block (Feed + Dashboard).
 */
function PageHeader({ title, subtitle, eyebrow, style }) {
  return (
    <header className="mb-6 animate-fade-up md:mb-8" style={style}>
      {eyebrow && (
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-ink-faint">{eyebrow}</p>
      )}
      <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">{title}</h1>
      {subtitle && <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-muted">{subtitle}</p>}
    </header>
  )
}

export default PageHeader
