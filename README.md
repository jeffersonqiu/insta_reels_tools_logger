# AI Tools Tracker

Personal full-stack tracker for AI tools discovered in Instagram Reels.

## What It Does

- Accepts a Reel URL through webhook (and optional Telegram bot fallback).
- Downloads audio with `yt-dlp`.
- Transcribes with AssemblyAI.
- Extracts structured tool records with Claude.
- Deduplicates and merges updates into Supabase.
- Shows tools in a mobile-first React UI with status tracking.

## Tech Stack

- Backend: FastAPI + Python 3.12 + `uv`
- DB: Supabase Postgres
- Frontend: React + Vite + Tailwind CSS
- Hosting: Railway (backend) + Vercel (frontend)

## Repository Layout

- `backend/`: API, ingestion, extraction, deduplication, migrations
- `frontend/`: UI for feed and video detail
- `CLAUDE.md`: canonical project instructions for Claude Code
- `agent.md`: pointer file for generic agents

## 1) Prerequisites

- Python 3.12+ available (project pins to 3.12 in backend)
- Node.js 18+
- Accounts:
  - Supabase
  - Anthropic API
  - AssemblyAI
  - Railway
  - Vercel
  - Telegram Bot (optional fallback)

## 2) Supabase Setup (From Scratch)

1. Create a new Supabase project.
2. Open **SQL Editor** and run `backend/db/migrations/001_initial.sql`, then `002_processing_error.sql` (adds `videos.processing_error` for debugging failed background jobs).
3. Enable RLS on all app tables (`videos`, `tools`, `video_tools`, `user_interactions`).
4. Create permissive policy for service-role-backed backend usage (personal app pattern).
   - Example policy shape:
     - Policy name: `service_role_all`
     - Action: all (`select`, `insert`, `update`, `delete`)
     - Using / Check: `auth.role() = 'service_role'`
5. Copy:
   - Project URL -> `SUPABASE_URL`
   - Service role key -> `SUPABASE_SERVICE_KEY`

## 3) Backend Setup

```bash
cd backend
cp .env.example .env
```

Fill `backend/.env`:

```env
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ASSEMBLYAI_API_KEY=
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
WEBHOOK_SECRET=
```

Run backend:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

### Pipeline preflight (do this before the webhook)

Run these **in order** so failures are easy to localize:

| Step | What | Command / URL |
|------|------|----------------|
| 1 | Health | `GET http://localhost:8000/health` |
| 2 | **AssemblyAI** (key + network, no download) | `GET http://localhost:8000/api/diagnostics/assemblyai` |
| 3 | Full checklist JSON | `GET http://localhost:8000/api/diagnostics/summary` |
| 4 | Ingest a Reel | `POST /api/webhook/reel` (see below) |

Examples:

```bash
curl -s http://localhost:8000/api/diagnostics/assemblyai | python3 -m json.tool
curl -s http://localhost:8000/api/diagnostics/summary | python3 -m json.tool
```

Interpretation:

- `"ok": true` on `/api/diagnostics/assemblyai` → key is accepted by AssemblyAI; safe to run the full pipeline.
- `"ok": false` → read `message` and `hint`; fix `ASSEMBLYAI_API_KEY` in `.env` (no extra quotes/spaces), restart uvicorn, retry step 2.

## 4) Frontend Setup

Create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Run frontend:

```bash
cd frontend
npm install
npm run dev
```

### If the UI looks unchanged (old counts, no “Watch Reel”)

1. **Confirm the browser talks to the backend you think** — open DevTools → Network, reload `/`, and check the request host for `GET /api/tools`. It must match where you run FastAPI (usually `localhost:8000`). If `VITE_API_BASE_URL` points at **Railway/Vercel**, deploy or pull latest code there, or set `.env.local` to `http://localhost:8000` and **restart** `npm run dev` (Vite reads env only at startup).
2. **Hard refresh** the tab: macOS **Cmd+Shift+R** (or disable cache in DevTools and reload).
3. **Restart the Vite dev server** after `git pull` or API/frontend changes: stop `npm run dev` (**Ctrl+C**) and start it again — Vite only reads `.env.local` at startup, and a full restart avoids a stuck HMR bundle.
4. **Restart uvicorn** after pulling backend changes (`--reload` usually picks up `routers/tools.py` automatically).

### “Seen in 2 videos” but only one Reel

Instagram URLs often differ only by `?igsh=…` or a trailing `/`. Those are **two rows** in `videos` (unique on full URL) but the **same reel**. The API deduplicates by canonical path for counts and **Watch Reel** links. To clean the DB, delete the duplicate `videos` row you don’t need (CASCADE removes orphan `video_tools` links).

## 5) API Smoke Test (Webhook — after diagnostics pass)

```bash
curl -X POST http://localhost:8000/api/webhook/reel \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/REEL_ID/",
    "secret": "YOUR_WEBHOOK_SECRET"
  }'
```

Expected:
- First time: `{"status":"processing"}`
- Duplicate URL: `{"status":"already_processed"}`

## 6) iOS Shortcut Setup

1. Open Shortcuts app and create shortcut: `Track AI Reels`.
2. Configure first block:
   - Receive input: `URLs`
   - Source: `Share Sheet`
   - If no input: `Continue`
3. Add **Get Shortcut Input**.
4. Add **Get Contents of URL**:
   - URL: `https://your-backend-domain/api/webhook/reel`
   - Method: `POST`
   - Body: `JSON`
   - Field `url`: Shortcut Input
   - Field `secret`: your webhook secret
5. Add **Show Content**.
6. Enable **Show in Share Sheet** in shortcut details.

## 7) Optional Telegram Fallback

Telegram integration is optional and only needed if iOS Shortcut is not enough.

- Bot logic file: `backend/services/telegram_bot.py`
- It detects `instagram.com/reel/...` links and forwards them to webhook.

## 8) Tests

Backend:

```bash
cd backend
uv run pytest
```

Frontend:

```bash
cd frontend
npm test
```

## 9) Deployment

**Step-by-step (Railway + Vercel + iOS Shortcut):** see **[DEPLOYMENT.md](./DEPLOYMENT.md)** in the repo root.

Summary:

- **Railway:** Root directory `backend`, use `backend/Dockerfile`, set all env vars from `.env.example`.
- **Vercel:** Root directory `frontend`, `VITE_API_BASE_URL=https://<your-railway-host>` (no trailing slash).
- **Procfile** (non-Docker): `web: uv run uvicorn main:app --host 0.0.0.0 --port $PORT`

## v2 Roadmap

- Add persistent retry queue abstraction (`JobStore` + `RetryPolicy`) beyond in-process retry.
- Add auth middleware for secured `/api` access if app expands beyond personal use.
- Add configurable UI density preference toggle.
- Add optional tag governance flow for novel tags.
