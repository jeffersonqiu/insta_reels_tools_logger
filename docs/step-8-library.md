# Step 8: knowledge library

The header now links to **Library** at `/library`. Existing Tools (`/`), Overview (`/dashboard`), and Video Detail (`/videos/:id`) routes remain supported.

## Browse and revisit

- Newest saved knowledge items appear first with title, summary, tags, saved date, and takeaway/action counts.
- Search matches titles, summaries, ideas, concepts, action items, tags, extracted tool descriptions, and repository names/descriptions/URLs. Matching is a case-insensitive substring search. Tags use any-match filtering, combined with search.
- Search and tag choices are stored in the URL and preserved when opening an item and returning to Library.
- `/items/:id` displays summary, ideas, actions, concepts, extracted tools, repositories/links, source Reel, video details, caption and transcript. Empty optional sections are omitted; caption/transcript start collapsed. Tool statuses and notes continue to be managed in Tools.
- Only HTTP(S) URLs are clickable. Missing or unsafe extracted links remain plain text; the UI never invents a repository URL.
- Loading, empty, no-match, error, not-found, refresh, and retry states are supported. Pending requests are cancelled on navigation.
- The existing warm dark styling and responsive layout are retained.

## API and scope

`GET /api/items` retains its JSON-array response and default limit of 50 (maximum 200), adding `offset` (default 0, nonnegative). Ordering is `created_at DESC, id DESC`, so equal creation times have stable pagination. Existing callers and item detail response shapes are unchanged.

Library reads successive 200-row pages before enabling results, then searches/filters locally. This avoids silently omitting older items from a personal library. It does not implement semantic search or paid backfill. A repeated full page fails visibly rather than causing an endless request loop. Offset pagination is a snapshot assembled from multiple reads; use Refresh to see new arrivals during a load. For a much larger library, move filtering and cursor pagination to the server.

No schema migration or paid processing is required. Historical Tools records do not automatically become knowledge items; the opt-in paid backfill remains separate.

## Checks and deployment

Run all backend tests, then `npm ci`, `npm run lint`, `npm test`, and `npm run build` in `frontend/`. Pinned GitHub workflows run backend tests and frontend checks. Fixes to pre-existing conditional Overview hooks and Node configuration linting allow the full frontend lint to pass.

Deploy the backend pagination change before or with the UI. The Cloudflare frontend build must still use the existing production `VITE_API_BASE_URL`. Verify `/library`, a real `/items/:id` deep link, search/no-match/tag clearing, Tools and Overview on desktop and phone widths. Read-only UI checks need no new Reel submission.
