# AI Tools Tracker

## Objective

**Turn Instagram Reels about AI tools into a searchable, personal inbox you control.**  
Share a Reel URL (iOS Shortcut or webhook), and the pipeline downloads audio, transcribes it, extracts structured tool records with Claude, deduplicates against what you already have in Supabase, and shows everything in a small **mobile-first** web app where you mark items as *to explore*, *implemented*, or *not interested*.

This repo is a **personal** full-stack tracker—not a generic scraper product. It is built to stay cheap, low-maintenance, and easy to extend in code.

---

## Screenshots

Stylized previews of the shipped UI (dark theme, filters, tool cards, video detail). Replace these SVGs under `docs/screenshots/` with your own PNG captures if you want pixel-perfect repo thumbnails.

| Feed | Video detail |
|------|----------------|
| ![Feed — tool inbox with status filters and cards](docs/screenshots/feed.svg) | ![Video — source URL and transcript area](docs/screenshots/video-detail.svg) |

---

## What you get

- Webhook ingestion of an Instagram Reel URL (+ optional Telegram bot forwarding).
- Audio via **yt-dlp** → transcription via **AssemblyAI** → extraction via **Claude** → **Supabase** Postgres with deduplication.
- React UI: feed with filters/tags, per-tool status, and a video page with source link and transcript tooling.

---

## Table of contents

1. [Tech stack](#tech-stack)
2. [Repository layout](#repository-layout)
3. [Prerequisites](#1-prerequisites)
4. [Supabase setup](#2-supabase-setup-from-scratch)
5. [Backend setup](#3-backend-setup)
6. [Frontend setup](#4-frontend-setup)
7. [API smoke test (webhook)](#5-api-smoke-test-webhook--after-diagnostics-pass)
8. [iOS Shortcut](#6-ios-shortcut-setup)
9. [Optional Telegram](#7-optional-telegram-fallback)
10. [Tests](#8-tests)
11. [Deployment](#9-deployment)
12. [v2 roadmap](#v2-roadmap)

---

## Tech stack

| Layer | Choice |
|--------|--------|
| Backend | FastAPI · Python 3.12 · `uv` |
| Database | Supabase (Postgres) |
| Frontend | React · Vite · Tailwind CSS |
| Hosting | Railway (API) · Vercel (UI) |

---

## Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | API, ingestion, extraction, deduplication, SQL migrations |
| `frontend/` | Feed + video detail UI |
| `docs/screenshots/` | README visuals (SVG previews; optional PNGs) |
| `CLAUDE.md` | Canonical instructions for Claude Code / agents |
| `agent.md` | Pointer for generic agents |
| `DEPLOYMENT.md` | Railway + Vercel + iOS Shortcut checklist |

---

## 1) Prerequisites

- Python 3.12+ (project pins 3.12 in backend)
- Node.js 18+
- Accounts: Supabase, Anthropic, AssemblyAI, Railway, Vercel; optional Telegram bot

---

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
   - Project URL → `SUPABASE_URL`
   - Service role key → `SUPABASE_SERVICE_KEY`

---

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

---

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

---

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

---

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

---

## 7) Optional Telegram Fallback

Telegram integration is optional and only needed if iOS Shortcut is not enough.

- Bot logic file: `backend/services/telegram_bot.py`
- It detects `instagram.com/reel/...` links and forwards them to webhook.

---

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

---

## 9) Deployment

**Step-by-step (Railway + Vercel + iOS Shortcut):** see **[DEPLOYMENT.md](./DEPLOYMENT.md)** in the repo root.

Summary:

- **Railway:** Either leave **root directory empty** and use the repo-root **`Dockerfile`** (builds `backend/`), **or** set root directory to **`backend`** and use **`backend/Dockerfile`**. See **DEPLOYMENT.md** if Railpack fails on the monorepo.
- **Vercel:** Root directory `frontend`, `VITE_API_BASE_URL=https://<your-railway-host>` (no trailing slash).
- **Procfile** (non-Docker): `web: uv run uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## v2 Roadmap

- Add persistent retry queue abstraction (`JobStore` + `RetryPolicy`) beyond in-process retry.
- Add auth middleware for secured `/api` access if app expands beyond personal use.
- Add configurable UI density preference toggle.
- Add optional tag governance flow for novel tags.
