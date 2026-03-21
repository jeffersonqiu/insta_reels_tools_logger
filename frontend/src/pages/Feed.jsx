import React, { useCallback, useEffect, useMemo, useState } from 'react'

import client from '../api/client'
import FilterTabs from '../components/FilterTabs'
import TagFilter from '../components/TagFilter'
import ToolCard from '../components/ToolCard'

const DEFAULT_COUNTS = { to_explore: 0, implemented: 0, not_interested: 0, all: 0 }

function LoadingGrid() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className="animate-fade-up rounded-xl border border-stroke bg-elevated/50 p-3 shadow-card"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          <div className="h-5 w-4/5 animate-pulse rounded bg-white/[0.06]" />
          <div className="mt-2 h-2 w-1/4 animate-pulse rounded bg-white/[0.04]" />
          <div className="mt-3 space-y-1.5">
            <div className="h-2.5 w-full animate-pulse rounded bg-white/[0.04]" />
            <div className="h-2.5 w-11/12 animate-pulse rounded bg-white/[0.04]" />
          </div>
        </div>
      ))}
    </div>
  )
}

function Feed() {
  const [activeTab, setActiveTab] = useState('to_explore')
  const [tools, setTools] = useState([])
  const [counts, setCounts] = useState(DEFAULT_COUNTS)
  const [allTags, setAllTags] = useState([])
  const [selectedTags, setSelectedTags] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refreshCounts = useCallback(async () => {
    try {
      const { data } = await client.get('/api/tools/counts')
      if (data && typeof data === 'object') {
        setCounts({
          to_explore: data.to_explore ?? 0,
          implemented: data.implemented ?? 0,
          not_interested: data.not_interested ?? 0,
          all: data.all ?? 0,
        })
      }
    } catch {
      /* keep previous counts */
    }
  }, [])

  const loadTags = useCallback(async () => {
    try {
      const { data } = await client.get('/api/tools/tags')
      if (Array.isArray(data)) setAllTags(data)
    } catch {
      setAllTags([])
    }
  }, [])

  useEffect(() => {
    loadTags()
    refreshCounts()
  }, [loadTags, refreshCounts])

  useEffect(() => {
    let mounted = true
    const fetchTools = async () => {
      setLoading(true)
      setError('')
      try {
        const { data } = await client.get('/api/tools', { params: { status: activeTab } })
        if (mounted) setTools(Array.isArray(data) ? data : [])
      } catch {
        if (mounted) setError('Failed to load tools.')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchTools()
    return () => {
      mounted = false
    }
  }, [activeTab])

  const filteredTools = useMemo(() => {
    if (!selectedTags.length) return tools
    return tools.filter((t) => {
      const ttags = t.tags || []
      return selectedTags.some((sel) => ttags.includes(sel))
    })
  }, [tools, selectedTags])

  const onStatusChanged = useCallback(
    (toolId, newStatus) => {
      if (activeTab !== 'all' && newStatus !== activeTab) {
        setTools((prev) => prev.filter((t) => t.id !== toolId))
      } else {
        setTools((prev) => prev.map((item) => (item.id === toolId ? { ...item, status: newStatus } : item)))
      }
      refreshCounts()
    },
    [activeTab, refreshCounts],
  )

  const toggleTag = useCallback((tag) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]))
  }, [])

  const clearTags = useCallback(() => setSelectedTags([]), [])

  return (
    <section>
      <div className="mb-2 animate-fade-up">
        <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">Your tool feed</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-muted">
          Scan cards quickly—expand for details. Filter by tag or status.
        </p>
      </div>
      <FilterTabs activeTab={activeTab} counts={counts} onChange={setActiveTab} />
      <TagFilter allTags={allTags} selectedTags={selectedTags} onToggle={toggleTag} onClear={clearTags} />
      {loading && <LoadingGrid />}
      {error && (
        <p className="animate-fade-up rounded-xl border border-coral/30 bg-coral-dim px-4 py-3 text-sm font-medium text-coral">
          {error}
        </p>
      )}
      {!loading && !error && filteredTools.length === 0 && (
        <div
          className="animate-fade-up rounded-2xl border border-dashed border-stroke bg-elevated/40 px-6 py-12 text-center backdrop-blur-sm"
          style={{ animationDelay: '80ms' }}
        >
          <p className="font-display text-lg font-semibold text-ink">Nothing matches</p>
          <p className="mx-auto mt-2 max-w-sm text-sm text-ink-muted">
            {selectedTags.length > 0
              ? 'Try clearing tag filters or pick another tab.'
              : 'No tools in this tab yet. Ingest a reel or switch filters.'}
          </p>
        </div>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filteredTools.map((tool, index) => (
          <ToolCard
            key={tool.id}
            tool={tool}
            onStatusChanged={onStatusChanged}
            style={{ animationDelay: `${80 + index * 45}ms` }}
          />
        ))}
      </div>
    </section>
  )
}

export default Feed
