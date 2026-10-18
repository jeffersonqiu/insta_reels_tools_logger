import React, { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'

import client from '../api/client'
import { savedDate, webUrl } from '../lib/knowledge'

function TextList({ title, values }) {
  if (!values?.length) return null
  return (
    <section className="rounded-2xl border border-stroke bg-elevated/90 p-5 shadow-card">
      <h2 className="font-display text-lg font-semibold">{title}</h2>
      <ul className="mt-3 list-disc space-y-3 pl-5 text-sm leading-relaxed text-ink-muted">
        {values.map((value, index) => <li key={index}>{value}</li>)}
      </ul>
    </section>
  )
}

function ItemDetail() {
  const { id } = useParams()
  const { search } = useLocation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await client.get(`/api/items/${encodeURIComponent(id)}`, { signal: controller.signal })
        if (!response.data?.item) throw new Error('Invalid item response')
        if (!controller.signal.aborted) setData(response.data)
      } catch (err) {
        if (!controller.signal.aborted) setError([404, 422].includes(err.response?.status) ? 'This item could not be found.' : 'Could not load this item. Please try again.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    load()
    return () => controller.abort()
  }, [id, retry])

  const back = <Link to={`/library${search}`} className="inline-flex min-h-[44px] items-center text-sm text-accent hover:underline">← Back to library</Link>
  if (loading) return <div>{back}<p role="status" className="py-12 text-ink-muted">Loading saved knowledge…</p></div>
  if (error) return <div>{back}<div role="alert" className="mt-4 rounded-xl border border-coral/30 bg-coral-dim p-5 text-coral"><p>{error}</p><button type="button" onClick={() => setRetry((value) => value + 1)} className="mt-3 min-h-[44px] underline">Try again</button></div></div>
  if (!data) return null
  const { item, video } = data
  const tools = item.raw_extraction?.tools || []
  const source = webUrl(item.source_url)

  return (
    <article className="space-y-6">
      <header>
        {back}
        <p className="mt-4 font-mono text-[11px] uppercase tracking-wider text-ink-faint">Instagram Reel · Saved {savedDate(item.created_at)}</p>
        <h1 className="mt-3 max-w-4xl font-display text-3xl font-bold leading-tight tracking-tight md:text-4xl">{item.title || 'Untitled Reel'}</h1>
        <div className="mt-4 flex flex-wrap gap-3">{(item.topics || []).map((topic) => <Link key={topic.id} to={`/topics/${topic.id}`} className="text-sm text-accent hover:underline">{topic.name} →</Link>)}</div>
        <div className="mt-4 flex flex-wrap gap-2">{(item.tags || []).map((tag) => <span key={tag} className="rounded-md bg-accent-dim px-2.5 py-1 text-xs text-accent">{tag}</span>)}</div>
      </header>
      {!!item.review_reasons?.length && <section className="rounded-2xl border border-accent/30 bg-elevated/90 p-5"><h2 className="font-display text-lg font-semibold">Needs review</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-muted">{item.review_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></section>}
      <section className="rounded-2xl border border-accent/25 bg-elevated/90 p-5 shadow-card sm:p-6">
        <h2 className="font-display text-lg font-semibold">Summary</h2>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink-muted">{item.summary || 'No summary saved.'}</p>
      </section>
      <div className="grid items-start gap-6 md:grid-cols-2">
        <TextList title="Key ideas" values={item.key_ideas} />
        <TextList title="Action items" values={item.action_items} />
      </div>
      <TextList title="Concepts" values={item.concepts} />
      {tools.length > 0 && (
        <section className="rounded-2xl border border-stroke bg-elevated/90 p-5 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-display text-lg font-semibold">Tools mentioned</h2><Link to="/" className="text-sm text-accent hover:underline">Manage in Tools →</Link></div>
          <div className="mt-4 space-y-5">{tools.map((tool, index) => <div key={index}><h3 className="font-semibold">{tool.name}</h3><p className="mt-2 text-sm leading-relaxed text-ink-muted">{tool.functionality}</p>{tool.problem_solved && <p className="mt-2 border-l-2 border-mint/40 pl-3 text-sm text-ink-muted">Solves: {tool.problem_solved}</p>}</div>)}</div>
        </section>
      )}
      {(item.repositories || []).length > 0 && (
        <section className="rounded-2xl border border-stroke bg-elevated/90 p-5 shadow-card">
          <h2 className="font-display text-lg font-semibold">Repositories & links</h2>
          <ul className="mt-4 space-y-4">{item.repositories.map((repo, index) => {
            const url = webUrl(repo.url)
            return <li key={index}>{url ? <a href={url} target="_blank" rel="noopener noreferrer" className="break-words font-semibold text-accent underline-offset-4 hover:underline">{repo.name} ↗</a> : <span className="font-semibold">{repo.name}</span>}{repo.description && <p className="mt-1 text-sm leading-relaxed text-ink-muted">{repo.description}</p>}{url ? <p className="mt-1 break-all font-mono text-xs text-ink-faint">{url}</p> : <p className="mt-1 text-xs text-ink-faint">No web link provided in the source.</p>}</li>
          })}</ul>
        </section>
      )}
      <section className="rounded-2xl border border-stroke bg-elevated/60 p-5">
        <h2 className="font-display text-lg font-semibold">Source</h2>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-3 text-sm text-accent">
          {source && <a href={source} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-[44px] items-center hover:underline">Watch Reel ↗</a>}
          {video && <Link to={`/videos/${encodeURIComponent(video.id)}`} className="inline-flex min-h-[44px] items-center hover:underline">Video details & tool statuses →</Link>}
        </div>
        {video?.video_created_at && <p className="mt-2 text-sm text-ink-muted">Posted {video.video_created_at}</p>}
        {[['Instagram caption', video?.caption], ['Transcript', video?.transcript]].map(([title, text]) => text ? <details key={title} className="mt-4 border-t border-stroke pt-4"><summary className="cursor-pointer py-2 text-sm font-medium">{title}</summary><p className="mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed text-ink-muted">{text}</p></details> : null)}
        {!video && <p className="mt-3 text-sm text-ink-muted">Source details are unavailable.</p>}
      </section>
    </article>
  )
}

export default ItemDetail
