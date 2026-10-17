// Extracted URLs are untrusted text. Only ordinary web links are clickable.
export function webUrl(value) {
  if (typeof value !== 'string') return null
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

export function matchesKnowledge(item, query, tags) {
  if (tags.length && !tags.some((tag) => (item.tags || []).includes(tag))) return false
  const needle = query.trim().toLowerCase()
  if (!needle) return true
  const text = [
    item.title, item.summary, ...(item.tags || []), ...(item.key_ideas || []),
    ...(item.concepts || []), ...(item.action_items || []),
    ...(item.repositories || []).flatMap((repo) => [repo.name, repo.description, repo.url]),
    ...(item.raw_extraction?.tools || []).flatMap((tool) => [tool.name, tool.functionality, tool.problem_solved]),
  ].filter(Boolean).join(' ').toLowerCase()
  return text.includes(needle)
}

export function savedDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown date' : date.toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}
