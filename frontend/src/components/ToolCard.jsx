import { useEffect, useState } from 'react'

import client from '../api/client'
import StatusButton from './StatusButton'

function ToolCard({ tool, onStatusChanged, style }) {
  const [status, setStatus] = useState(tool.status || 'to_explore')
  const [expanded, setExpanded] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setStatus(tool.status || 'to_explore')
  }, [tool.id, tool.status])

  const seenInVideoCount = Array.isArray(tool.source_videos)
    ? tool.source_videos.length
    : typeof tool.video_count === 'number'
      ? tool.video_count
      : (tool.source_video_ids || []).length

  const firstReel = (tool.source_videos || [])[0]
  const tags = tool.tags || []

  const updateStatus = async (nextStatus) => {
    const previous = status
    setStatus(nextStatus)
    setIsSaving(true)
    setError('')
    try {
      await client.patch(`/api/tools/${tool.id}/interaction`, {
        status: nextStatus,
        notes: tool.notes || null,
      })
      onStatusChanged?.(tool.id, nextStatus)
    } catch {
      try {
        await client.patch(`/api/tools/${tool.id}/interaction`, {
          status: nextStatus,
          notes: tool.notes || null,
        })
        onStatusChanged?.(tool.id, nextStatus)
      } catch {
        setStatus(previous)
        setError('Update failed. Please try again.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <article
      style={style}
      className="group relative overflow-hidden rounded-xl border border-stroke bg-elevated/90 shadow-card backdrop-blur-md transition duration-300 animate-fade-up hover:border-accent/20 hover:shadow-card-hover"
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/45 to-transparent opacity-80"
        aria-hidden
      />

      {/* Header row: title + expand */}
      <div className="flex items-start justify-between gap-2 p-3 pb-2 md:p-4 md:pb-2">
        <h3 className="min-w-0 flex-1 font-display text-base font-semibold leading-snug tracking-tight text-ink">
          <span className="line-clamp-2 text-balance md:line-clamp-1">{tool.name}</span>
        </h3>
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="shrink-0 rounded-lg border border-stroke bg-white/[0.04] px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-muted transition hover:border-accent/25 hover:text-accent"
          aria-expanded={expanded}
        >
          {expanded ? 'Less' : 'More'}
        </button>
      </div>

      <p className="px-3 font-mono text-[10px] font-medium uppercase tracking-wider text-ink-faint md:px-4">
        {tool.first_seen_date || 'Unknown'}
      </p>

      <p className="mt-2 line-clamp-2 px-3 text-xs leading-relaxed text-ink-muted md:px-4">
        {tool.functionality || 'No functionality captured yet.'}
      </p>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-stroke/80 px-3 pb-1 pt-3 md:px-4">
          <p className="border-l-2 border-accent/35 pl-2.5 text-xs italic leading-relaxed text-ink-muted/95">
            <span className="mb-1 block font-mono not-italic text-[10px] font-semibold uppercase tracking-wider text-ink-faint">
              Solves
            </span>
            {tool.problem_solved || 'No problem statement captured yet.'}
          </p>
          {(tool.source_videos || []).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {tool.source_videos.map((sv, i) => (
                <a
                  key={sv.video_id}
                  href={sv.instagram_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded-lg border border-stroke bg-white/[0.05] px-2.5 py-1 font-mono text-[11px] font-medium text-accent transition hover:border-accent/30 hover:bg-accent-dim"
                >
                  <span>Reel {tool.source_videos.length > 1 ? `${i + 1}` : ''}</span>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3 opacity-80">
                    <path d="M6.22 8.72a.75.75 0 0 0 1.06 1.06l5.22-5.22v1.69a.75.75 0 0 0 1.5 0v-3.5a.75.75 0 0 0-.75-.75h-3.5a.75.75 0 0 0 0 1.5h1.69L6.22 8.72Z" />
                    <path d="M3.5 6.75c0-.69.56-1.25 1.25-1.25H7A.75.75 0 0 0 7 4H4.75A2.75 2.75 0 0 0 2 6.75v4.5A2.75 2.75 0 0 0 4.75 14h4.5A2.75 2.75 0 0 0 12 11.25V9a.75.75 0 0 0-1.5 0v2.25c0 .69-.56 1.25-1.25 1.25h-4.5c-.69 0-1.25-.56-1.25-1.25v-4.5Z" />
                  </svg>
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tags — show fewer when collapsed */}
      {tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5 px-3 md:px-4">
          {(expanded ? tags : tags.slice(0, 4)).map((tag) => (
            <span
              key={`${tool.id}-${tag}`}
              className="rounded border border-accent/15 bg-accent-dim/60 px-1.5 py-0.5 font-mono text-[10px] font-medium text-accent/95"
            >
              {tag}
            </span>
          ))}
          {!expanded && tags.length > 4 && (
            <span className="self-center font-mono text-[10px] text-ink-faint">+{tags.length - 4}</span>
          )}
        </div>
      )}

      {/* Footer: meta + quick watch + actions */}
      <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-stroke/70 px-3 py-2.5 md:px-4">
        <span className="font-mono text-[10px] text-ink-faint">
          <span className="font-semibold text-ink-muted">{seenInVideoCount}</span> vid
        </span>
        {firstReel && !expanded && (
          <a
            href={firstReel.instagram_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-md border border-stroke bg-white/[0.05] px-2 py-0.5 font-mono text-[10px] font-medium text-accent hover:border-accent/25"
          >
            Watch
            {seenInVideoCount > 1 ? ` (+${seenInVideoCount - 1})` : ''}
          </a>
        )}
        <div className="ml-auto flex flex-wrap justify-end gap-1.5">
          <StatusButton variant="success" onClick={() => updateStatus('implemented')}>
            Done
          </StatusButton>
          <StatusButton variant="danger" onClick={() => updateStatus('not_interested')}>
            Skip
          </StatusButton>
          {status !== 'to_explore' && (
            <StatusButton variant="accent" onClick={() => updateStatus('to_explore')}>
              Explore
            </StatusButton>
          )}
        </div>
      </div>

      {isSaving && (
        <p className="px-3 pb-2 font-mono text-[10px] text-ink-faint md:px-4">
          <span className="inline-block h-1 w-1 animate-pulse rounded-full bg-accent align-middle" /> Saving…
        </p>
      )}
      {error && <p className="px-3 pb-2 text-[11px] font-medium text-coral md:px-4">{error}</p>}
    </article>
  )
}

export default ToolCard
