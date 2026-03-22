import React from 'react'

/**
 * KPI tile with Syne numerals + chart accent (mint / amber / orange).
 */
function StatCard({ label, value, hint, accent = 'mint', style }) {
  const accents = {
    mint: 'from-chart-1-dim/40 text-chart-1 border-chart-1/25',
    amber: 'from-chart-2-dim/40 text-chart-2 border-chart-2/25',
    orange: 'from-chart-3-dim/40 text-chart-3 border-chart-3/25',
    violet: 'from-accent-dim text-accent border-accent/25',
  }
  const cls = accents[accent] || accents.mint

  return (
    <div
      style={style}
      className={`animate-fade-up relative overflow-hidden rounded-2xl border bg-gradient-to-br to-transparent p-4 shadow-card backdrop-blur-sm md:p-5 touch-manipulation ${cls}`}
    >
      <p className="font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint">{label}</p>
      <p className="font-stat mt-2 text-4xl font-extrabold tabular-nums tracking-tight md:text-5xl">{value}</p>
      {hint && <p className="mt-2 text-xs leading-snug text-ink-muted">{hint}</p>}
    </div>
  )
}

export default StatCard
