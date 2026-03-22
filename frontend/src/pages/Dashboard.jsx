import React, { useEffect, useMemo, useState } from 'react'

import client from '../api/client'
import BarList from '../components/shell/BarList'
import PageHeader from '../components/shell/PageHeader'
import Panel from '../components/shell/Panel'
import StatCard from '../components/shell/StatCard'
import { CHART_FILL } from '../theme/chartColors'

function SeriesChart({ series }) {
  if (!series || !series.length) {
    return <p className="text-sm text-ink-muted">No activity in this window yet.</p>
  }

  const maxV = useMemo(() => Math.max(...series.map((d) => d.videos_processed || 0), 1), [series])
  const maxT = useMemo(() => Math.max(...series.map((d) => d.distinct_tools_linked || 0), 1), [series])

  return (
    <div className="flex min-h-[140px] items-end gap-1.5 sm:gap-2">
      {series.map((day) => {
        const hV = Math.max(8, Math.round((day.videos_processed / maxV) * 100))
        const hT = Math.max(8, Math.round((day.distinct_tools_linked / maxT) * 100))
        const label = day.date.slice(5)
        return (
          <div key={day.date} className="flex min-w-0 flex-1 flex-col items-center gap-2">
            <div className="flex h-24 w-full items-end justify-center gap-0.5 sm:h-28">
              <div
                className="w-[42%] max-w-[14px] min-h-[4px] rounded-t-sm transition-all"
                style={{ height: `${hV}%`, backgroundColor: CHART_FILL.c1 }}
                title={`${day.videos_processed} reels`}
              />
              <div
                className="w-[42%] max-w-[14px] min-h-[4px] rounded-t-sm transition-all"
                style={{ height: `${hT}%`, backgroundColor: CHART_FILL.c2 }}
                title={`${day.distinct_tools_linked} tools`}
              />
            </div>
            <span className="font-mono text-[9px] text-ink-faint sm:text-[10px]">{label}</span>
          </div>
        )
      })}
    </div>
  )
}

function StatusBars({ breakdown }) {
  if (!breakdown) return null
  const total = breakdown.all || 1
  const rows = [
    { key: 'to_explore', label: 'To explore', count: breakdown.to_explore, fill: CHART_FILL.accent },
    { key: 'implemented', label: 'Implemented', count: breakdown.implemented, fill: CHART_FILL.mint },
    { key: 'not_interested', label: 'Not interested', count: breakdown.not_interested, fill: CHART_FILL.coral },
  ]
  return (
    <ul className="space-y-4">
      {rows.map((row) => {
        const pct = Math.round((row.count / total) * 100)
        return (
          <li key={row.key}>
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="text-ink-muted">{row.label}</span>
              <span className="font-mono tabular-nums text-ink">
                {row.count}{' '}
                <span className="text-ink-faint">({pct}%)</span>
              </span>
            </div>
            <div className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full min-w-[2px] rounded-full"
                style={{ width: `${pct}%`, backgroundColor: row.fill }}
              />
            </div>
          </li>
        )
      })}
    </ul>
  )
}

function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const { data: payload } = await client.get('/api/metrics/overview')
        if (mounted) setData(payload)
      } catch {
        if (mounted) setError('Could not load metrics. Is the API up to date?')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    run()
    return () => {
      mounted = false
    }
  }, [])

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        subtitle="Last 7 days of ingestion, tag mix across your library, and triage status."
      />

      {loading && (
        <div className="grid animate-pulse grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 rounded-2xl border border-stroke bg-elevated/40" />
          ))}
        </div>
      )}

      {error && (
        <p className="rounded-xl border border-coral/30 bg-coral-dim px-4 py-3 text-sm font-medium text-coral">{error}</p>
      )}

      {!loading && !error && data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              style={{ animationDelay: '60ms' }}
              accent="mint"
              label="Reels processed (7d)"
              value={data.videos_last_7d}
              hint="By ingestion time (processed_at)."
            />
            <StatCard
              style={{ animationDelay: '120ms' }}
              accent="amber"
              label="Tool mentions (7d)"
              value={data.tool_mentions_last_7d}
              hint={`${data.distinct_tools_in_new_reels_7d ?? 0} distinct tools linked from those reels.`}
            />
            <StatCard
              style={{ animationDelay: '180ms' }}
              accent="orange"
              label="New tool rows (7d)"
              value={data.tools_first_seen_last_7d}
              hint="Distinct tools with first_seen in the last week."
            />
            <StatCard
              style={{ animationDelay: '240ms' }}
              accent="violet"
              label="Implemented"
              value={`${data.implemented_pct ?? 0}%`}
              hint={`${data.status_breakdown?.implemented ?? 0} of ${data.status_breakdown?.all ?? 0} tools marked done.`}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel
              style={{ animationDelay: '280ms' }}
              className="animate-fade-up"
              title="Tag prevalence"
              subtitle="How often each tag appears across all tools in your library."
            >
              <BarList items={data.tag_prevalence || []} />
            </Panel>

            <Panel
              style={{ animationDelay: '320ms' }}
              className="animate-fade-up"
              title="Triage mix"
              subtitle="Share of tools by your status (entire library)."
            >
              <StatusBars breakdown={data.status_breakdown} />
            </Panel>
          </div>

          <Panel
            style={{ animationDelay: '360ms' }}
            className="animate-fade-up"
            title="Last 7 calendar days"
            subtitle="Per day: teal = reels processed, amber = distinct tools linked to those reels."
          >
            <SeriesChart series={data.series_last_7d || []} />
          </Panel>
        </>
      )}
    </section>
  )
}

export default Dashboard
