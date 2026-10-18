import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import client from '../api/client'
import PageHeader from '../components/shell/PageHeader'
import { savedDate } from '../lib/knowledge'

function SourceList({ title, rows }) {
  if (!rows?.length) return null
  return (
    <section className="rounded-2xl border border-stroke bg-elevated/90 p-5">
      <h2 className="font-display text-xl font-semibold">{title}</h2>
      <ul className="mt-4 space-y-5">{rows.slice(0, 10).map((row, index) => (
        <li key={index}><p className="text-sm leading-relaxed text-ink-muted">{row.text}</p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">{row.sources.map((source) => <Link key={source.id} to={`/items/${encodeURIComponent(source.id)}`} className="text-xs text-accent hover:underline">{source.title || 'Read source'} →</Link>)}</div>
        </li>
      ))}</ul>
      {rows.length > 10 && <p className="mt-4 text-xs text-ink-faint">Showing 10 of {rows.length}. Open the sources below for all takeaways.</p>}
    </section>
  )
}

function Topics() {
  const { topicId } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const { data: result } = await client.get(topicId ? `/api/topics/${encodeURIComponent(topicId)}` : '/api/topics', { signal: controller.signal })
        if (!topicId && !Array.isArray(result)) throw new Error('Invalid topic list')
        if (topicId && (!result?.id || !Array.isArray(result.items))) throw new Error('Invalid topic')
        if (!controller.signal.aborted) setData(result)
      } catch (err) {
        if (!controller.signal.aborted) setError(err.response?.status === 404 ? 'This topic could not be found.' : 'Could not load your topics. Please try again.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    load()
    return () => controller.abort()
  }, [topicId, refresh])

  const back = <Link to={topicId ? '/topics' : '/library'} className="inline-flex min-h-[44px] items-center text-sm text-accent hover:underline">← {topicId ? 'All topics' : 'All saved knowledge'}</Link>
  const stale = data && (topicId ? data.id !== topicId : !Array.isArray(data))
  if (loading || (!error && stale)) return <div>{back}<p role="status" className="py-12 text-ink-muted">Organizing your saved knowledge…</p></div>
  if (error) return <div>{back}<div role="alert" className="mt-4 rounded-xl border border-coral/30 p-5"><p>{error}</p><button type="button" onClick={() => setRefresh((value) => value + 1)} className="mt-3 min-h-[44px] text-accent underline">Try again</button></div></div>
  if (!data) return null
  if (!topicId) return (
    <section aria-label="Knowledge topics">
      <PageHeader eyebrow="Your knowledge base" title="Browse by topic" subtitle="Find related ideas together, revisit their sources, and choose something to try." />
      <p className="mb-5 text-sm text-ink-muted">Topics are broad shelves; tags describe finer details. A source can belong to more than one topic.</p>
      <div className="grid gap-4 sm:grid-cols-2">{data.filter((topic) => !topic.catch_all).map((topic) => (
        <article key={topic.id} className="rounded-2xl border border-stroke bg-elevated/90 p-5 shadow-card">
          <p className="mb-3 font-mono text-xs text-ink-faint">{topic.count} saved {topic.count === 1 ? 'source' : 'sources'}</p>
          <h2 className="font-display text-xl font-semibold"><Link to={`/topics/${topic.id}`} className="text-accent hover:underline">{topic.name}</Link></h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-muted">{topic.description}</p>
        </article>
      ))}</div>
      <section className="mt-8" aria-label="Weekly tidy-up queues">
        <h2 className="font-display text-xl font-semibold">For the weekly tidy-up</h2>
        <p className="mt-2 text-sm text-ink-muted">Unclear items stay visible until they can be organized or their source questions resolved.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">{data.filter((topic) => topic.catch_all).map((topic) => (
          <article key={topic.id} className="rounded-2xl border border-accent/30 bg-elevated/70 p-5"><h3 className="font-display text-lg font-semibold"><Link to={`/topics/${topic.id}`} className="text-accent hover:underline">{topic.name} · {topic.count}</Link></h3><p className="mt-2 text-sm leading-relaxed text-ink-muted">{topic.description}</p></article>
        ))}</div>
      </section>
      <div className="mt-5">{back}</div>
    </section>
  )
  return (
    <article className="space-y-6">
      <header>{back}<PageHeader eyebrow="Topic guide" title={data.name} subtitle={data.description} /></header>
      <section className="rounded-2xl border border-accent/25 bg-elevated/90 p-5"><h2 className="font-display text-xl font-semibold">How to use this shelf</h2><p className="mt-3 text-sm leading-relaxed text-ink-muted">{data.guide}</p></section>
      <div className="grid items-start gap-6 md:grid-cols-2"><SourceList title="Ideas to connect" rows={data.ideas} /><SourceList title="Things to try" rows={data.actions} /></div>
      <section><h2 className="font-display text-xl font-semibold">Sources · {data.items.length}</h2>
        {!data.items.length ? <p className="mt-4 text-sm text-ink-muted">This shelf is clear for now. New matching items will appear here automatically.</p> : (
          <div className="mt-4 grid gap-4 md:grid-cols-2">{data.items.map((item) => (
            <article key={item.id} className="rounded-2xl border border-stroke bg-elevated/90 p-5">
              <p className="font-mono text-xs text-ink-faint">Saved {savedDate(item.created_at)}</p>
              <h3 className="mt-3 font-display text-lg font-semibold"><Link to={`/items/${encodeURIComponent(item.id)}`} className="text-accent hover:underline">{item.title || 'Untitled source'}</Link></h3>
              <p className="mt-3 text-sm leading-relaxed text-ink-muted">{item.summary}</p>
              {!!item.review_reasons?.length && <div className="mt-4 rounded-xl border border-accent/30 p-3"><p className="text-sm font-medium text-accent">Needs review</p><ul className="mt-2 list-disc space-y-2 pl-4 text-sm text-ink-muted">{item.review_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>}
            </article>
          ))}</div>
        )}
      </section>
    </article>
  )
}

export default Topics
