import React from 'react'

const TABS = [
  { key: 'to_explore', label: 'To Explore' },
  { key: 'implemented', label: 'Implemented' },
  { key: 'not_interested', label: 'Not Interested' },
  { key: 'all', label: 'All' },
]

function FilterTabs({ activeTab, counts, onChange }) {
  return (
    <div className="mb-8 animate-fade-up rounded-2xl border border-stroke bg-elevated/80 p-1.5 shadow-card backdrop-blur-md md:inline-flex md:flex-wrap">
      <div className="grid grid-cols-2 gap-1 sm:grid-cols-4 md:flex md:flex-wrap">
        {TABS.map((tab) => {
          const selected = activeTab === tab.key
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => onChange(tab.key)}
              className={`relative min-h-[48px] touch-manipulation rounded-xl px-4 py-3 text-left text-sm font-medium transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-accent active:scale-[0.99] md:min-h-[52px] md:text-center ${
                selected
                  ? 'bg-accent-dim text-accent shadow-[inset_0_0_0_1px_rgba(196,181,253,0.35)]'
                  : 'text-ink-muted hover:bg-white/[0.04] hover:text-ink'
              }`}
            >
              <span className="block">{tab.label}</span>
              <span
                className={`mt-0.5 block font-mono text-[11px] font-semibold tabular-nums ${
                  selected ? 'text-accent/90' : 'text-ink-faint'
                }`}
              >
                {counts[tab.key] ?? 0}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default FilterTabs
