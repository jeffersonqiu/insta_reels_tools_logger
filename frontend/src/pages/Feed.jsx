import React from 'react'
import { useEffect, useMemo, useState } from 'react'

import client from '../api/client'
import FilterTabs from '../components/FilterTabs'
import ToolCard from '../components/ToolCard'

function Feed() {
  const [activeTab, setActiveTab] = useState('to_explore')
  const [tools, setTools] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    const fetchTools = async () => {
      setLoading(true)
      setError('')
      try {
        const { data } = await client.get(`/api/tools?status=${activeTab}`)
        if (mounted) setTools(data)
      } catch (_err) {
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

  const counts = useMemo(() => {
    const c = { to_explore: 0, implemented: 0, not_interested: 0, all: tools.length }
    for (const t of tools) {
      if (c[t.status] !== undefined) c[t.status] += 1
    }
    return c
  }, [tools])

  const onStatusChanged = (toolId, status) => {
    setTools((prev) => prev.map((item) => (item.id === toolId ? { ...item, status } : item)))
  }

  return (
    <section>
      <FilterTabs activeTab={activeTab} counts={counts} onChange={setActiveTab} />
      {loading && <p className="text-sm text-gray-400">Loading tools...</p>}
      {error && <p className="text-sm text-rose-400">{error}</p>}
      {!loading && !error && tools.length === 0 && (
        <p className="rounded-md border border-gray-800 bg-gray-900 p-4 text-sm text-gray-400">No tools found for this filter.</p>
      )}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {tools.map((tool) => (
          <ToolCard key={tool.id} tool={tool} onStatusChanged={onStatusChanged} />
        ))}
      </div>
    </section>
  )
}

export default Feed
