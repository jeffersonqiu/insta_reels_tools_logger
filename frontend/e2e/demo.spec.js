// @ts-check
import { test, expect } from '@playwright/test'

const overview = {
  videos_last_7d: 9,
  tool_mentions_last_7d: 20,
  distinct_tools_in_new_reels_7d: 15,
  tools_first_seen_last_7d: 15,
  tag_prevalence: [
    { tag: 'productivity', count: 16 },
    { tag: 'devtools', count: 13 },
    { tag: 'agents', count: 10 },
  ],
  status_breakdown: { all: 20, to_explore: 14, implemented: 6, not_interested: 0 },
  implemented_pct: 30,
  series_last_7d: Array.from({ length: 7 }, (_, i) => {
    const d = new Date(Date.UTC(2026, 2, 22 + i))
    return {
      date: d.toISOString().slice(0, 10),
      videos_processed: i % 3,
      distinct_tools_linked: (i % 2) + 1,
    }
  }),
}

const toolsList = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    name: 'Self-Fixing Software System',
    functionality: 'Automated repair loops for dev workflows.',
    problem_solved: 'Reduce manual debugging.',
    tags: ['agents', 'coding', 'devtools'],
    first_seen_date: '2026-03-26',
    status: 'to_explore',
    notes: null,
    source_videos: [],
    video_count: 1,
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'MCP servers',
    functionality: 'Claude Code and JSON schema for MCP.',
    problem_solved: null,
    tags: ['productivity', 'devtools'],
    first_seen_date: '2026-03-25',
    status: 'to_explore',
    notes: null,
    source_videos: [],
    video_count: 1,
  },
]

function filterToolsByQuery(list, q) {
  if (!q || !q.trim()) return list
  const n = q.trim().toLowerCase()
  return list.filter(
    (t) =>
      t.name.toLowerCase().includes(n) ||
      (t.functionality && t.functionality.toLowerCase().includes(n)) ||
      (t.problem_solved && t.problem_solved.toLowerCase().includes(n)) ||
      (t.tags || []).some((tag) => tag.toLowerCase().includes(n)),
  )
}

async function setupApiMocks(page) {
  await page.route('**/api/metrics/overview', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(overview) })
  })
  await page.route('**/api/tools/counts', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ to_explore: 2, implemented: 0, not_interested: 0, all: 2 }),
    })
  })
  await page.route('**/api/tools/tags', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(['agents', 'coding', 'devtools', 'productivity']),
    })
  })
  await page.route((url) => {
    try {
      const u = new URL(url)
      return u.pathname === '/api/tools'
    } catch {
      return false
    }
  }, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback()
      return
    }
    const u = new URL(route.request().url())
    const q = u.searchParams.get('q') || ''
    const list = filterToolsByQuery(toolsList, q)
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(list) })
  })
  await page.route('**/api/tools/*/interaction', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ tool_id: 'x', status: 'to_explore', notes: null, updated_at: new Date().toISOString() }),
    })
  })
}

test.describe('AI Tools Tracker demo', () => {
  test('overview, tools feed, and search', async ({ page }) => {
    await setupApiMocks(page)
    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible({ timeout: 15_000 })
    await page.waitForTimeout(600)

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Tools', exact: true }).click()
    await expect(page.getByTestId('tool-search')).toBeVisible()
    await expect(page.getByText('Self-Fixing Software System')).toBeVisible()

    await page.getByTestId('tool-search').fill('MCP')
    await expect(page.getByText('MCP servers')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('text=Self-Fixing Software System')).toHaveCount(0)
    await page.waitForTimeout(500)
  })
})
