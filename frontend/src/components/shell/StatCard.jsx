import React from 'react'

import { STAT_CARD_ACCENTS } from '../../theme/chartColors'

/**
 * KPI tile with Syne numerals + chart accent (mint / amber / orange).
 */
function StatCard({ label, value, hint, accent = 'mint', style }) {
  const palette = STAT_CARD_ACCENTS[accent] || STAT_CARD_ACCENTS.mint

  return (
    <div
      style={{
        border: palette.border,
        backgroundImage: palette.backgroundImage,
        ...style,
      }}
      className="animate-fade-up relative overflow-hidden rounded-2xl bg-transparent p-4 shadow-card backdrop-blur-sm md:p-5 touch-manipulation"
    >
      <p className="font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint">{label}</p>
      <p
        className="font-stat mt-2 text-4xl font-extrabold tabular-nums tracking-tight md:text-5xl"
        style={{ color: palette.valueColor }}
      >
        {value}
      </p>
      {hint && <p className="mt-2 text-xs leading-snug text-ink-muted">{hint}</p>}
    </div>
  )
}

export default StatCard
