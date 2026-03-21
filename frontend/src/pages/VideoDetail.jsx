import React from 'react'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

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
      } catch (_err) {
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

  if (loading) return <p className="text-sm text-gray-400">Loading video...</p>
  if (error) return <p className="text-sm text-rose-400">{error}</p>
  if (!data) return null

  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <a href={data.instagram_url} target="_blank" rel="noreferrer" className="text-sm text-violet-300 hover:underline">
          {data.instagram_url}
        </a>
        <p className="mt-2 text-xs text-gray-500">Date: {data.video_created_at || 'Unknown'}</p>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <button className="text-sm text-violet-300 hover:underline" onClick={() => setShowTranscript((v) => !v)}>
          {showTranscript ? 'Hide transcript' : 'Show transcript'}
        </button>
        {showTranscript && <p className="mt-3 whitespace-pre-wrap text-sm text-gray-200">{data.transcript || 'No transcript.'}</p>}
      </div>

      <div className="space-y-2">
        {(data.tools || []).map((tool) => (
          <div key={tool.id} className="rounded-xl border border-gray-800 bg-gray-900 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-semibold">{tool.name}</h3>
              <span className="rounded-full bg-violet-500/20 px-2 py-1 text-xs text-violet-300">{tool.status || 'to_explore'}</span>
            </div>
            <p className="mt-2 text-sm text-gray-300">{tool.functionality}</p>
            <p className="mt-1 text-sm italic text-gray-400">Solves: {tool.problem_solved}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export default VideoDetail
