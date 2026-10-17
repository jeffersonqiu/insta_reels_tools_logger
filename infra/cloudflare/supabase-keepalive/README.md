# supabase-keepalive

Tiny Cloudflare Worker that calls the production backend's `GET /health/db` on a schedule.

## Purpose

- Generates lightweight, legitimate Supabase activity so the Free project is less likely to pause from inactivity.
- Gives a simple recurring availability check.

## Architecture

```
Cloudflare Cron ──▶ this Worker ──▶ Railway FastAPI /health/db ──▶ Supabase
```

- Separate from the frontend Worker. No secrets, no bindings, no Supabase credentials.
- One function (`checkDatabaseHealth`) is used by both the `scheduled` and `fetch` handlers.
- Any 2xx = success (logs `Database health check OK`). Non-2xx logs only the HTTP status; timeouts (12s) and network errors are logged server-side. Response bodies are never logged or returned.
- `fetch` returns `200 {"status":"ok"}` or `503 {"status":"unavailable"}`.

## Cron schedule

`0 */8 * * *` (UTC): 00:00, 08:00, 16:00 — 3 runs/day. Defined in `wrangler.jsonc`.

## Local / manual testing

```bash
npm install
npm run dev                      # wrangler dev --test-scheduled
curl localhost:8787/             # -> {"status":"ok"}
curl 'localhost:8787/__scheduled?cron=0+*/8+*+*+*'   # simulate the cron
```

After deployment: `curl https://supabase-keepalive.<your-subdomain>.workers.dev/`

## Deployment

```bash
cd infra/cloudflare/supabase-keepalive
npm install
npx wrangler login   # first time only
npm run deploy       # = wrangler deploy
```

The Worker name is `supabase-keepalive`; it won't touch the frontend Worker.

## Log inspection

- Dashboard: Workers & Pages → `supabase-keepalive` → Observability / Logs (observability is enabled in `wrangler.jsonc`). Cron runs appear under Settings → Triggers → Cron Triggers, and in Logs as invocations with the `scheduled` trigger.
- Live: `npx wrangler tail supabase-keepalive`

## Disable / remove

- Stop the cron only: set `"triggers": { "crons": [] }` in `wrangler.jsonc` and redeploy (or delete the trigger in the dashboard).
- Remove entirely: `npx wrangler delete supabase-keepalive`, then delete this directory.
