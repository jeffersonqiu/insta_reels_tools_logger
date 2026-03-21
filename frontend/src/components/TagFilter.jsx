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
            className="font-mono text-[11px] font-medium text-accent underline-offset-2 hover:underline"
          >
            Clear ({selectedTags.length})
          </button>
        )}
      </div>
      <div className="mt-3 flex max-h-28 flex-wrap gap-2 overflow-y-auto pr-1 md:max-h-none">
        {allTags.map((tag) => {
          const on = selectedTags.includes(tag)
          return (
            <button
              key={tag}
              type="button"
              onClick={() => onToggle(tag)}
              className={`rounded-lg border px-2.5 py-1 font-mono text-[11px] font-medium transition ${
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
