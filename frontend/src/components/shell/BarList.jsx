import React from 'react'

import { BAR_FILL } from '../../theme/chartColors'

/**
 * Horizontal bar rows (tag prevalence, etc.) — CSS-only, no chart lib.
 */
function BarList({ items, valueKey = 'count', labelKey = 'tag', emptyMessage = 'No data yet.' }) {
  if (!items || !items.length) {
    return <p className="text-sm text-ink-muted">{emptyMessage}</p>
  }

  const max = Math.max(...items.map((i) => Number(i[valueKey]) || 0), 1)

  return (
    <ul className="space-y-3" role="list">
      {items.map((item) => {
        const v = Number(item[valueKey]) || 0
        const pct = Math.round((v / max) * 100)
        const label = item[labelKey]
        return (
          <li key={String(label)}>
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="min-w-0 truncate font-medium text-ink">{label}</span>
              <span className="shrink-0 font-mono tabular-nums text-ink-muted">{v}</span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full min-w-[2px] rounded-full transition-all duration-500"
                style={{ width: `${pct}%`, backgroundColor: BAR_FILL }}
                role="presentation"
              />
            </div>
          </li>
        )
      })}
    </ul>
  )
}

export default BarList
