import { useCallback, useState } from 'react'

import client from '../api/client'

const STATUS_OPTIONS = [
  { value: 'to_explore', label: 'To explore' },
  { value: 'implemented', label: 'Implemented' },
  { value: 'not_interested', label: 'Not interested' },
]

function reelCount(tool) {
  if (Array.isArray(tool.source_videos)) return tool.source_videos.length
  if (typeof tool.video_count === 'number') return tool.video_count
  return (tool.source_video_ids || []).length
}

function ToolsTable({ tools, onStatusChanged }) {
  const [savingId, setSavingId] = useState(null)
  const [errorById, setErrorById] = useState({})

  const patchStatus = useCallback(
    async (tool, nextStatus) => {
      setSavingId(tool.id)
      setErrorById((prev) => ({ ...prev, [tool.id]: '' }))
      try {
        await client.patch(`/api/tools/${tool.id}/interaction`, {
          status: nextStatus,
          notes: tool.notes || null,
        })
        onStatusChanged?.(tool.id, nextStatus)
      } catch {
        setErrorById((prev) => ({ ...prev, [tool.id]: 'Update failed' }))
      } finally {
        setSavingId(null)
      }
    },
    [onStatusChanged],
  )

  if (!tools.length) {
    return null
  }

  return (
    <div className="animate-fade-up overflow-x-auto rounded-xl border border-stroke bg-elevated/80 shadow-card backdrop-blur-md">
      <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-stroke bg-white/[0.03]">
            <th scope="col" className="px-3 py-3 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint sm:px-4">
              Name
            </th>
            <th scope="col" className="px-3 py-3 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint sm:px-4">
              Status
            </th>
            <th scope="col" className="hidden px-3 py-3 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint md:table-cell sm:px-4">
              Tags
            </th>
            <th scope="col" className="px-3 py-3 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint sm:px-4">
              Reels
            </th>
            <th scope="col" className="hidden px-3 py-3 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint lg:table-cell sm:px-4">
              First seen
            </th>
            <th scope="col" className="hidden px-3 py-3 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-faint xl:table-cell sm:px-4">
              Notes
            </th>
          </tr>
        </thead>
        <tbody>
          {tools.map((tool) => {
            const tags = tool.tags || []
            const notes = tool.notes || ''
            const notesShort = notes.length > 56 ? `${notes.slice(0, 56)}…` : notes
            return (
              <tr key={tool.id} className="border-b border-stroke/70 last:border-0">
                <td className="max-w-[12rem] px-3 py-3 align-top font-medium text-ink sm:max-w-xs sm:px-4">
                  <span className="line-clamp-2">{tool.name}</span>
                </td>
                <td className="px-3 py-3 align-top sm:px-4">
                  <label htmlFor={`status-${tool.id}`} className="sr-only">
                    Status for {tool.name}
                  </label>
                  <select
                    id={`status-${tool.id}`}
                    value={tool.status || 'to_explore'}
                    disabled={savingId === tool.id}
                    onChange={(e) => patchStatus(tool, e.target.value)}
                    className="min-h-[44px] w-full max-w-[11rem] touch-manipulation rounded-lg border border-stroke bg-canvas-deep/80 px-2 py-2 text-xs text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  {errorById[tool.id] ? (
                    <p className="mt-1 text-[11px] font-medium text-coral">{errorById[tool.id]}</p>
                  ) : null}
                </td>
                <td className="hidden max-w-[10rem] px-3 py-3 align-top text-xs text-ink-muted md:table-cell sm:px-4">
                  {tags.length ? tags.join(', ') : '—'}
                </td>
                <td className="px-3 py-3 align-top font-mono tabular-nums text-ink-muted sm:px-4">{reelCount(tool)}</td>
                <td className="hidden px-3 py-3 align-top font-mono text-xs text-ink-muted lg:table-cell sm:px-4">
                  {tool.first_seen_date || '—'}
                </td>
                <td className="hidden max-w-[14rem] px-3 py-3 align-top text-xs text-ink-muted xl:table-cell sm:px-4" title={notes || undefined}>
                  {notesShort || '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default ToolsTable
