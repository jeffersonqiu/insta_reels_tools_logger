import React from 'react'

const TABS = [
  { key: 'to_explore', label: 'To Explore' },
  { key: 'implemented', label: 'Implemented' },
  { key: 'not_interested', label: 'Not Interested' },
  { key: 'all', label: 'All' },
]

function FilterTabs({ activeTab, counts, onChange }) {
  return (
    <div className="mb-4 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
      {TABS.map((tab) => {
        const selected = activeTab === tab.key
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`rounded-md border px-3 py-2 text-sm ${
              selected
                ? 'border-violet-500 bg-violet-500/20 text-violet-300'
                : 'border-gray-700 bg-gray-900 text-gray-300 hover:bg-gray-800'
            }`}
          >
            {tab.label} <span className="ml-1 text-xs text-gray-400">({counts[tab.key] ?? 0})</span>
          </button>
        )
      })}
    </div>
  )
}

export default FilterTabs
