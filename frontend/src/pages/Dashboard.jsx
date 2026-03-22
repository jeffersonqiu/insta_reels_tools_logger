import React, { useEffect, useMemo, useState } from 'react'

import client from '../api/client'
import BarList from '../components/shell/BarList'
import PageHeader from '../components/shell/PageHeader'
import Panel from '../components/shell/Panel'
import StatCard from '../components/shell/StatCard'
import { BAR_FILL, SERIES } from '../theme/chartColors'

function barHeightPct(value, max) {
  if (!max || value <= 0) return 0
  return Math.max(10, Math.round((value / max) * 100))
}

function SeriesChart({ series }) {
  if (!series || !series.length) {
    return <p className="text-sm text-ink-muted">No activity in this window yet.</p>
  }

  const maxV = useMemo(() => Math.max(...series.map((d) => d.videos_processed || 0), 1), [series])
  const maxT = useMemo(() => Math.max(...series.map((d) => d.distinct_tools_linked || 0), 1), [series])
  const n = series.length
  const gridStyle = { display: 'grid', gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))`, gap: '0.35rem' }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-ink-muted">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: SERIES.reels }} aria-hidden />
          Reels processed (that day)
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: SERIES.toolsLinked }} aria-hidden />
          Distinct tools linked to those reels
        </span>
      </div>

      <div className="flex gap-2 sm:gap-3">
        <div className="flex w-[7.25rem] shrink-0 flex-col sm:w-32">
          <div className="flex h-24 items-end pb-1 sm:h-28">
            <span className="text-[10px] font-medium leading-tight text-ink-muted">Reels processed</span>
          </div>
          <div className="flex h-24 items-end pb-1 sm:h-28">
            <span className="text-[10px] font-medium leading-tight text-ink-muted">Tools linked</span>
          </div>
          <div className="h-5 shrink-0" aria-hidden />
        </div>

        <div className="min-w-0 flex-1 space-y-0">
          <div style={gridStyle}>
            {series.map((day) => {
              const hV = barHeightPct(day.videos_processed || 0, maxV)
              return (
                <div key={`${day.date}-r`} className="flex h-24 flex-col items-center justify-end sm:h-28">
                  <div
                    className="w-[55%] max-w-[18px] rounded-t-sm transition-all"
                    style={{
                      height: hV ? `${hV}%` : 0,
                      minHeight: hV ? 3 : 0,
                      backgroundColor: SERIES.reels,
                    }}
                    title={`${day.videos_processed} reels`}
                  />
                </div>
              )
            })}
          </div>
          <div style={gridStyle}>
            {series.map((day) => {
              const hT = barHeightPct(day.distinct_tools_linked || 0, maxT)
              return (
                <div key={`${day.date}-t`} className="flex h-24 flex-col items-center justify-end sm:h-28">
                  <div
                    className="w-[55%] max-w-[18px] rounded-t-sm transition-all"
                    style={{
                      height: hT ? `${hT}%` : 0,
                      minHeight: hT ? 3 : 0,
                      backgroundColor: SERIES.toolsLinked,
                    }}
                    title={`${day.distinct_tools_linked} tools`}
                  />
                </div>
              )
            })}
          </div>
          <div className="pt-1" style={gridStyle}>
            {series.map((day) => (
              <span
                key={`${day.date}-lbl`}
                className="block text-center font-mono text-[9px] text-ink-faint sm:text-[10px]"
              >
                {day.date.slice(5)}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusBars({ breakdown }) {
  if (!breakdown) return null
  const total = breakdown.all || 1
  const rows = [
    { key: 'to_explore', label: 'To explore', count: breakdown.to_explore },
    { key: 'implemented', label: 'Implemented', count: breakdown.implemented },
    { key: 'not_interested', label: 'Not interested', count: breakdown.not_interested },
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
              {row.count > 0 && pct > 0 ? (
                <div
                  className="h-full min-w-[2px] rounded-full"
                  style={{ width: `${pct}%`, backgroundColor: BAR_FILL }}
                />
              ) : null}
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
              label="Reels processed (7d)"
              value={data.videos_last_7d}
              hint="Reels with processed_at in the last 7 days (rolling, UTC)."
            />
            <StatCard
              style={{ animationDelay: '120ms' }}
              label="Mentions in new reels (7d)"
              value={data.tool_mentions_last_7d}
              hint={`${data.distinct_tools_in_new_reels_7d ?? 0} distinct tools linked — each video↔tool row in video_tools counts once.`}
            />
            <StatCard
              style={{ animationDelay: '180ms' }}
              label="Tools first logged (7d)"
              value={data.tools_first_seen_last_7d}
              hint="By tools.first_seen_date vs same 7d cutoff as reels. Older tools can still get new mentions."
            />
            <StatCard
              style={{ animationDelay: '240ms' }}
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
            subtitle="UTC dates. Each day: reels ingested vs distinct tools linked to those reels (see legend below)."
          >
            <SeriesChart series={data.series_last_7d || []} />
          </Panel>
        </>
      )}
    </section>
  )
}

export default Dashboard
