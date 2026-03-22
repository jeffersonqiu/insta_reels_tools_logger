import React, { useEffect, useMemo, useState } from 'react'

import client from '../api/client'
import BarList from '../components/shell/BarList'
import PageHeader from '../components/shell/PageHeader'
import Panel from '../components/shell/Panel'
import StatCard from '../components/shell/StatCard'
import { BAR_FILL, SERIES } from '../theme/chartColors'

/** Pixel height for bar area; values map to this via shared max. */
const CHART_INNER_PX = 112

function SeriesChart({ series }) {
  if (!series || !series.length) {
    return <p className="text-sm text-ink-muted">No activity in this window yet.</p>
  }

  const maxV = useMemo(() => Math.max(...series.map((d) => d.videos_processed || 0), 0), [series])
  const maxT = useMemo(() => Math.max(...series.map((d) => d.distinct_tools_linked || 0), 0), [series])
  const scaleMax = Math.max(maxV, maxT, 1)

  const barHeight = (n) => {
    const v = Number(n) || 0
    if (v <= 0) return 0
    return Math.max(4, Math.round((v / scaleMax) * CHART_INNER_PX))
  }

  return (
    <div className="space-y-4">
      <p className="text-xs leading-relaxed text-ink-muted">
        <strong className="font-medium text-ink">How to read this:</strong> each date has{' '}
        <strong>two separate bars side by side</strong> — not stacked. Left = reels processed that day; right =
        distinct tools linked to those reels. Numbers above each bar are the exact counts. Bar heights use one scale
        (0–{scaleMax}) so you can compare across days.
      </p>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ink-muted">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: SERIES.reels }} aria-hidden />
          Reels (left bar)
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-sm border border-stroke"
            style={{ backgroundColor: SERIES.toolsLinked }}
            aria-hidden
          />
          Tools linked (right bar)
        </span>
      </div>

      <div className="flex gap-2 sm:gap-3">
        {/* Y-axis */}
        <div
          className="flex w-9 shrink-0 flex-col justify-between pb-6 text-right font-mono text-[10px] tabular-nums text-ink-faint sm:w-10"
          aria-hidden
        >
          <span>{scaleMax}</span>
          <span className="text-ink-faint/70">0</span>
        </div>

        <div className="min-w-0 flex-1">
          <div
            className="flex items-end justify-between gap-1 border-b border-stroke pb-px sm:gap-1.5"
            style={{ minHeight: CHART_INNER_PX }}
            role="img"
            aria-label="Reels and tools linked per UTC calendar day"
          >
            {series.map((day) => {
              const v = day.videos_processed || 0
              const t = day.distinct_tools_linked || 0
              const hV = barHeight(v)
              const hT = barHeight(t)
              return (
                <div key={day.date} className="flex min-w-0 flex-1 flex-col items-center justify-end gap-1">
                  <div className="flex w-full items-end justify-center gap-0.5 sm:gap-1">
                    <div className="flex w-[42%] max-w-[22px] flex-col items-center gap-0.5">
                      <span className="font-mono text-[10px] font-semibold tabular-nums leading-none text-ink sm:text-[11px]">
                        {v}
                      </span>
                      <div
                        className="w-full min-w-0 rounded-t-[3px] transition-all"
                        style={{
                          height: hV,
                          minHeight: hV ? undefined : 0,
                          backgroundColor: SERIES.reels,
                        }}
                        title={`${v} reels`}
                      />
                    </div>
                    <div className="flex w-[42%] max-w-[22px] flex-col items-center gap-0.5">
                      <span className="font-mono text-[10px] font-semibold tabular-nums leading-none text-ink sm:text-[11px]">
                        {t}
                      </span>
                      <div
                        className="w-full min-w-0 rounded-t-[3px] transition-all"
                        style={{
                          height: hT,
                          minHeight: hT ? undefined : 0,
                          backgroundColor: SERIES.toolsLinked,
                        }}
                        title={`${t} tools`}
                      />
                    </div>
                  </div>
                  <span className="mt-1 font-mono text-[9px] tabular-nums text-ink-faint sm:text-[10px]">
                    {day.date.slice(5)}
                  </span>
                </div>
              )
            })}
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
            subtitle="UTC dates. Side-by-side bars per day — numbers show exact counts."
          >
            <SeriesChart series={data.series_last_7d || []} />
          </Panel>
        </>
      )}
    </section>
  )
}

export default Dashboard
