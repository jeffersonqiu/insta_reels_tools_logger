import { useState } from 'react'

import client from '../api/client'
import StatusButton from './StatusButton'

function ToolCard({ tool, onStatusChanged }) {
  const [status, setStatus] = useState(tool.status || 'to_explore')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')

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
    } catch (_err) {
      try {
        await client.patch(`/api/tools/${tool.id}/interaction`, {
          status: nextStatus,
          notes: tool.notes || null,
        })
        onStatusChanged?.(tool.id, nextStatus)
      } catch (_err2) {
        setStatus(previous)
        setError('Update failed. Please try again.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <article className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <h3 className="text-lg font-semibold">{tool.name}</h3>
      <p className="mt-1 text-xs text-gray-500">First seen: {tool.first_seen_date || 'Unknown'}</p>
      <p className="mt-3 text-sm text-gray-200">{tool.functionality || 'No functionality captured yet.'}</p>
      <p className="mt-2 text-sm italic text-gray-400">
        Solves: {tool.problem_solved || 'No problem statement captured yet.'}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {(tool.tags || []).map((tag) => (
          <span key={`${tool.id}-${tag}`} className="rounded-full bg-violet-500/20 px-2 py-1 text-xs text-violet-300">
            {tag}
          </span>
        ))}
      </div>
      <p className="mt-3 text-xs text-gray-500">Seen in {tool.video_count ?? (tool.source_video_ids || []).length} video(s)</p>
      {(tool.source_videos || []).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {tool.source_videos.map((sv, i) => (
            <a
              key={sv.video_id}
              href={sv.instagram_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-full bg-gray-800 px-3 py-1 text-xs text-violet-300 transition hover:bg-gray-700"
            >
              <span>Watch Reel{tool.source_videos.length > 1 ? ` ${i + 1}` : ''}</span>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3">
                <path d="M6.22 8.72a.75.75 0 0 0 1.06 1.06l5.22-5.22v1.69a.75.75 0 0 0 1.5 0v-3.5a.75.75 0 0 0-.75-.75h-3.5a.75.75 0 0 0 0 1.5h1.69L6.22 8.72Z" />
                <path d="M3.5 6.75c0-.69.56-1.25 1.25-1.25H7A.75.75 0 0 0 7 4H4.75A2.75 2.75 0 0 0 2 6.75v4.5A2.75 2.75 0 0 0 4.75 14h4.5A2.75 2.75 0 0 0 12 11.25V9a.75.75 0 0 0-1.5 0v2.25c0 .69-.56 1.25-1.25 1.25h-4.5c-.69 0-1.25-.56-1.25-1.25v-4.5Z" />
              </svg>
            </a>
          ))}
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusButton variant="success" onClick={() => updateStatus('implemented')}>
          ✅ Mark Implemented
        </StatusButton>
        <StatusButton variant="danger" onClick={() => updateStatus('not_interested')}>
          🚫 Not Interested
        </StatusButton>
        {status !== 'to_explore' && (
          <StatusButton variant="accent" onClick={() => updateStatus('to_explore')}>
            🔖 To Explore
          </StatusButton>
        )}
      </div>
      {isSaving && <p className="mt-2 text-xs text-gray-500">Saving...</p>}
      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
    </article>
  )
}

export default ToolCard
