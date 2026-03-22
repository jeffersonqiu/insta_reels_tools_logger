import React from 'react'

/**
 * Toggle tags to filter the current tab's tool list (client-side).
 */
function TagFilter({ allTags, selectedTags, onToggle, onClear }) {
  if (!allTags.length) return null

  return (
    <div className="mb-6 animate-fade-up rounded-2xl border border-stroke bg-elevated/60 px-4 py-3 backdrop-blur-md" style={{ animationDelay: '40ms' }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
          Tags <span className="font-normal text-ink-faint/80">(any match)</span>
        </span>
        {selectedTags.length > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="min-h-[44px] touch-manipulation font-mono text-[11px] font-medium text-accent underline-offset-2 hover:underline sm:min-h-0"
          >
            Clear ({selectedTags.length})
          </button>
        )}
      </div>
      <p className="mt-1 text-[10px] text-ink-faint md:hidden">Scroll tags vertically if the list is long.</p>
      <div
        className="mt-3 flex max-h-36 flex-wrap gap-2 overflow-y-auto overscroll-y-contain pr-1 [-webkit-overflow-scrolling:touch] md:max-h-none"
        style={{ touchAction: 'pan-y' }}
      >
        {allTags.map((tag) => {
          const on = selectedTags.includes(tag)
          return (
            <button
              key={tag}
              type="button"
              onClick={() => onToggle(tag)}
              className={`min-h-[40px] touch-manipulation rounded-lg border px-3 py-2 font-mono text-[11px] font-medium transition active:scale-[0.98] sm:min-h-0 sm:px-2.5 sm:py-1.5 ${
                on
                  ? 'border-accent/40 bg-accent-dim text-accent shadow-sm'
                  : 'border-stroke bg-white/[0.04] text-ink-muted hover:border-stroke hover:bg-white/[0.07] hover:text-ink'
              }`}
            >
              {tag}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default TagFilter
