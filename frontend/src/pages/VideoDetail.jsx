import React from 'react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import client from '../api/client'

function VideoDetail() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showTranscript, setShowTranscript] = useState(false)

  useEffect(() => {
    let mounted = true
    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await client.get(`/api/videos/${id}`)
        if (mounted) setData(response.data)
      } catch {
        if (mounted) setError('Failed to load video details.')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    run()
    return () => {
      mounted = false
    }
  }, [id])

  if (loading) {
    return (
      <div className="animate-fade-up space-y-4">
        <div className="h-4 w-32 animate-pulse rounded bg-white/[0.06]" />
        <div className="h-40 animate-pulse rounded-2xl border border-stroke bg-elevated/40" />
      </div>
    )
  }
  if (error) {
    return (
      <p className="animate-fade-up rounded-xl border border-coral/30 bg-coral-dim px-4 py-3 text-sm font-medium text-coral">
        {error}
      </p>
    )
  }
  if (!data) return null

  return (
    <section className="space-y-6">
      <div className="animate-fade-up">
        <Link
          to="/"
          className="group inline-flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wider text-ink-faint transition hover:text-accent"
        >
          <span className="transition group-hover:-translate-x-0.5">←</span> Back to feed
        </Link>
        <h1 className="font-display mt-4 text-3xl font-bold tracking-tight text-ink">Video</h1>
        <p className="mt-1 text-sm text-ink-muted">Source reel and extracted tools.</p>
      </div>

      <div className="animate-fade-up overflow-hidden rounded-2xl border border-stroke bg-elevated/90 p-5 shadow-card backdrop-blur-md" style={{ animationDelay: '60ms' }}>
        <a
          href={data.instagram_url}
          target="_blank"
          rel="noreferrer"
          className="break-all font-mono text-sm font-medium text-accent underline-offset-4 transition hover:underline"
        >
          {data.instagram_url}
        </a>
        <p className="mt-3 font-mono text-[11px] font-medium uppercase tracking-wider text-ink-faint">
          Recorded · {data.video_created_at || 'Unknown'}
        </p>
      </div>

      <div
        className="animate-fade-up overflow-hidden rounded-2xl border border-stroke bg-elevated/90 shadow-card backdrop-blur-md"
        style={{ animationDelay: '120ms' }}
      >
        <button
          type="button"
          className="flex w-full items-center justify-between px-5 py-4 text-left font-medium text-ink transition hover:bg-white/[0.03]"
          onClick={() => setShowTranscript((v) => !v)}
        >
          <span>Transcript</span>
          <span className="font-mono text-xs text-accent">{showTranscript ? 'Hide' : 'Show'}</span>
        </button>
        {showTranscript && (
          <div className="border-t border-stroke px-5 py-4">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-muted">{data.transcript || 'No transcript.'}</p>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <h2 className="animate-fade-up font-display text-lg font-semibold text-ink" style={{ animationDelay: '160ms', opacity: 0 }}>
          Tools in this video
        </h2>
        {(data.tools || []).map((tool, i) => (
          <div
            key={tool.id}
            className="animate-fade-up rounded-2xl border border-stroke bg-elevated/90 p-5 shadow-card backdrop-blur-md transition hover:border-accent/20"
            style={{ animationDelay: `${200 + i * 70}ms` }}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="font-display text-lg font-semibold tracking-tight text-ink">{tool.name}</h3>
              <span className="rounded-md border border-accent/25 bg-accent-dim px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wide text-accent">
                {tool.status || 'to_explore'}
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink-muted">{tool.functionality}</p>
            <p className="mt-2 border-l-2 border-mint/35 pl-3 text-sm italic text-ink-muted/90">Solves: {tool.problem_solved}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export default VideoDetail
