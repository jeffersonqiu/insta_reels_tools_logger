import React from 'react'

/**
 * KPI tile — neutral surface, monospace numerals, single accent (no per-card rainbow).
 */
function StatCard({ label, value, hint, style }) {
  return (
    <div
      style={style}
      className="animate-fade-up relative overflow-hidden rounded-2xl border border-stroke bg-elevated/90 p-4 shadow-card backdrop-blur-sm md:p-5 touch-manipulation"
    >
      <p className="font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint">{label}</p>
      <p className="font-mono mt-2 text-3xl font-semibold tabular-nums tracking-tight text-accent md:text-4xl">{value}</p>
      {hint && <p className="mt-2 text-xs leading-snug text-ink-muted">{hint}</p>}
    </div>
  )
}

export default StatCard
