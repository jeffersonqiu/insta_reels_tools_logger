import React, { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import client from '../api/client'
import PageHeader from '../components/shell/PageHeader'
import TagFilter from '../components/TagFilter'
import { matchesKnowledge, savedDate } from '../lib/knowledge'

const PAGE_SIZE = 200

function Library() {
  const [params, setParams] = useSearchParams()
  const query = params.get('q') || ''
  const selectedTags = params.getAll('tag')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const collected = new Map()
        // Read all pages so search and tags include older saved items too.
        for (let offset = 0; ; offset += PAGE_SIZE) {
          const { data } = await client.get('/api/items', {
            params: { limit: PAGE_SIZE, offset }, signal: controller.signal,
          })
          if (controller.signal.aborted) return
          if (!Array.isArray(data)) throw new Error('Invalid library response')
          const previousSize = collected.size
          for (const item of data) collected.set(item.id, item)
          if (data.length < PAGE_SIZE) break
          if (collected.size === previousSize) throw new Error('Library pagination did not advance')
        }
        setItems([...collected.values()])
      } catch {
        if (!controller.signal.aborted) setError('Could not load your library. Please try again.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    load()
    return () => controller.abort()
  }, [refresh])

  const allTags = useMemo(() => [...new Set(items.flatMap((item) => item.tags || []))].sort(), [items])
  const filtered = items.filter((item) => matchesKnowledge(item, query, selectedTags))
  const updateSearch = (value) => {
    const next = new URLSearchParams(params)
    if (value) next.set('q', value)
    else next.delete('q')
    setParams(next, { replace: true })
  }
  const toggleTag = (tag) => {
    const next = new URLSearchParams(params)
    next.delete('tag')
    const tags = selectedTags.includes(tag) ? selectedTags.filter((value) => value !== tag) : [...selectedTags, tag]
    tags.forEach((value) => next.append('tag', value))
    setParams(next, { replace: true })
  }
  const clearTags = () => {
    const next = new URLSearchParams(params)
    next.delete('tag')
    setParams(next, { replace: true })
  }

  return (
    <section aria-label="Your library">
      <PageHeader eyebrow="Saved knowledge" title="Your library" subtitle="Ideas worth keeping. Revisit the takeaways, tools, and next steps from your saved Reels." />
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label htmlFor="library-search" className="mb-2 block text-sm text-ink-muted">Search your library</label>
          <input
            id="library-search" type="search" value={query} onChange={(event) => updateSearch(event.target.value)}
            placeholder="Search ideas, tools, links, or tags…"
            className="tool-search-input min-h-[48px] w-full rounded-xl border border-stroke bg-elevated px-4 py-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
        </div>
        <button type="button" onClick={() => setRefresh((value) => value + 1)} disabled={loading}
          className="min-h-[48px] rounded-xl border border-stroke px-4 text-sm text-ink-muted hover:text-ink disabled:opacity-50">
          Refresh
        </button>
      </div>
      <TagFilter allTags={allTags} selectedTags={selectedTags} onToggle={toggleTag} onClear={clearTags} />
      {loading ? <p role="status" className="py-12 text-ink-muted">Loading your saved knowledge…</p> : error ? (
        <div role="alert" className="rounded-xl border border-coral/30 bg-coral-dim p-5 text-coral">
          <p>{error}</p>
          <button type="button" onClick={() => setRefresh((value) => value + 1)} className="mt-3 min-h-[44px] underline">Try again</button>
        </div>
      ) : (
        <>
          <p role="status" className="mb-4 text-sm text-ink-muted">
            {query || selectedTags.length ? `${filtered.length} of ${items.length}` : items.length} saved {items.length === 1 ? 'item' : 'items'} · newest first
          </p>
          {filtered.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-stroke bg-elevated/40 px-6 py-14 text-center">
              <h2 className="font-display text-xl font-semibold">{items.length ? 'No matching items' : 'Your library starts here'}</h2>
              <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-ink-muted">
                {items.length ? 'Try another search or clear your filters.' : 'Share a Reel using your existing Shortcut or Telegram bot. Its knowledge item will appear here after processing. Older saved Reels remain available in Tools.'}
              </p>
              {items.length > 0 && <button type="button" onClick={() => setParams({})} className="mt-4 min-h-[44px] text-accent underline">Clear filters</button>}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {filtered.map((item) => (
                <article key={item.id} className="rounded-2xl border border-stroke bg-elevated/90 p-5 shadow-card transition hover:border-accent/35">
                  <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-ink-faint">Instagram Reel · Saved {savedDate(item.created_at)}</p>
                  <h2 className="font-display text-xl font-semibold leading-snug">
                    <Link to={`/items/${encodeURIComponent(item.id)}${params.size ? `?${params}` : ''}`} className="rounded outline-none hover:text-accent focus-visible:ring-2 focus-visible:ring-accent">
                      {item.title || 'Untitled Reel'}
                    </Link>
                  </h2>
                  <p className="mt-3 line-clamp-4 text-sm leading-relaxed text-ink-muted">{item.summary || 'Open this item to view its saved knowledge.'}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {(item.tags || []).map((tag) => <span key={tag} className="rounded-md bg-accent-dim px-2 py-1 text-xs text-accent">{tag}</span>)}
                  </div>
                  <p className="mt-4 border-t border-stroke pt-3 text-xs text-ink-faint">{(item.key_ideas || []).length} key ideas · {(item.action_items || []).length} next steps</p>
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default Library
