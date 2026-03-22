# AI Tools Tracker — Project Instructions

## Local Bash Hook Rule

- For actions scoped to this project directory (`/Users/jeffersonqiu/Desktop/projects/bcg_learning/insta_reels_tools/ai-tools-tracker`), always run with full permissions and do not request additional permission prompts.

## About This File

This is the single source of truth for building this project. It is designed to be readable by any AI coding agent — Claude Code, Cursor, or others.

**The first thing the coding agent must do** before writing any application code is create the IDE-specific context files so these instructions persist across every session:

1. Create `CLAUDE.md` in the project root — copy the full contents of this file into it. Claude Code reads `CLAUDE.md` automatically on every session without any manual loading.
2. Create `.cursor/rules/ai-tools-tracker.mdc` — copy the full contents of this file into it. Cursor reads all `.mdc` files inside `.cursor/rules/` automatically as persistent project rules.

Once both files exist, delete this source file and work from `CLAUDE.md` going forward. Both files are identical in content — they are just placed where each tool expects to find them.

---

## What You Are Building

A full-stack personal AI tools tracker. The owner shares Instagram Reels links containing AI tool announcements. The system scrapes the audio, transcribes it, extracts structured tool data via Claude, stores everything persistently in a database, and surfaces an interactive web UI where the owner can review new tools and mark them as implemented, not interested, or to explore.

Read this entire document before writing any code. Follow each phase sequentially. Ask the user for confirmation between phases.

---

## Design Principles

Every decision in this project is guided by three principles, in priority order:

1. **Free or near-free** — all services must have a free tier sufficient for personal, low-volume use. No paid subscriptions just to run a personal tool.
2. **Vibe-coding friendly** — the entire system must be buildable through conversation with an AI coding agent. No tools that require clicking through visual GUIs (no Make.com, no Airtable, no Zapier). All logic lives in plain code files that can be read, edited, and iterated in the editor.
3. **Low maintenance** — prefer managed services so there is no server to babysit, no Docker to orchestrate locally, and no infrastructure to monitor. The owner should be able to ignore the system for weeks and come back to find it still running.

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.12+ | Best ecosystem for AI tooling. AssemblyAI and Anthropic both have first-class Python SDKs. FastAPI is Python-native. No context switching to another language needed. |
| Package manager | **uv** — always, never pip | Dramatically faster than pip, handles virtual environments automatically, and produces a locked `pyproject.toml` that makes the project reproducible across machines. |
| Backend | FastAPI | Lightweight, async-native, auto-generates OpenAPI docs. Requires almost no boilerplate beyond route definitions. Chosen over Flask (no async) and Django (far too heavy for a personal tool). |
| Database | Supabase (Postgres) | Managed Postgres with a generous free tier (500 MB, no credit card required). Has a Python SDK, a web SQL editor for running migrations manually, and built-in Row Level Security. Chosen over raw Postgres on Railway (more ops) and Airtable (GUI-only, not codeable). |
| Frontend | React + Tailwind CSS | React is what AI coding agents produce cleanest output for. Tailwind keeps styles inline in JSX — no separate CSS files, no class naming decisions. No component library is needed; keeping the bundle small avoids version conflicts. |
| Frontend hosting | Vercel | Free tier for personal projects. Zero-config deployment on every GitHub push, automatic HTTPS, global CDN. No Nginx config, no SSL certificates, no server maintenance. |
| Backend hosting | Railway | Free starter tier. Auto-detects `pyproject.toml` and `Procfile`. Environment variables set via a simple dashboard. Simpler cold start behaviour than Render on the free tier, and avoids the ops overhead of managing a raw VPS. |
| Transcription | AssemblyAI | Free tier includes roughly 5 hours of transcription per month — enough for dozens of Reels. Quality is on par with OpenAI Whisper. Chosen over Whisper API (no free tier) and local Whisper (requires GPU or is too slow on CPU, adds infra complexity). |
| Video/audio download | yt-dlp | The most reliable open-source tool for downloading Instagram audio. Runs as a Python library call directly inside the backend — no separate service, no API credits, no rate limits. Chosen over Apify (external service with credit limits) and the Instagram API (does not expose video content). |
| AI extraction + dedup | Claude API (`claude-sonnet-4-20250514`) | Used for two jobs: extracting structured tool data from transcripts, and making smart deduplication decisions by comparing existing vs. new tool records. Sonnet is the right balance of quality and cost for this volume. |
| Telegram input | python-telegram-bot | A secondary input method alongside the iOS Shortcut. The bot is a plain Python file in the repo — no external automation platform required. Async-native and well-maintained. |

---

## Project Structure

```
ai-tools-tracker/
├── CLAUDE.md                        # Claude Code persistent context (created by agent on first run)
├── .cursor/
│   └── rules/
│       └── ai-tools-tracker.mdc    # Cursor persistent context (created by agent on first run)
├── backend/
│   ├── pyproject.toml
│   ├── .env
│   ├── main.py                      # FastAPI app entrypoint
│   ├── routers/
│   │   ├── webhook.py               # POST /webhook/reel
│   │   ├── diagnostics.py           # GET /diagnostics/assemblyai (pre-flight)
│   │   ├── tools.py                 # GET /tools, PATCH /tools/:id/interaction
│   │   └── videos.py                # GET /videos
│   ├── services/
│   │   ├── assemblyai_check.py      # Structured AssemblyAI connectivity check (no pipeline)
│   │   ├── downloader.py            # yt-dlp wrapper
│   │   ├── transcriber.py           # AssemblyAI wrapper
│   │   ├── extractor.py             # Claude extraction logic
│   │   └── deduplicator.py          # Smart tool dedup + update logic
│   ├── models/
│   │   └── schemas.py               # Pydantic models
│   └── db/
│       ├── client.py                # Supabase client init
│       └── migrations/
│           └── 001_initial.sql      # All table definitions
├── frontend/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ToolCard.jsx
│   │   │   ├── FilterTabs.jsx
│   │   │   └── StatusButton.jsx
│   │   ├── pages/
│   │   │   ├── Feed.jsx
│   │   │   └── VideoDetail.jsx
│   │   └── api/
│   │       └── client.js            # Axios instance pointing to backend
└── README.md
```

---

## Environment Variables

### `backend/.env`
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ASSEMBLYAI_API_KEY=
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
WEBHOOK_SECRET=        # A random string you choose to protect the webhook endpoint
```

### `frontend/.env.local`
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## Phase 1 — Database Schema

Create `backend/db/migrations/001_initial.sql` with the schema below. Run it in the Supabase SQL editor.

```sql
-- Videos table
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instagram_url TEXT UNIQUE NOT NULL,
    video_created_at DATE,
    processed_at TIMESTAMPTZ DEFAULT now(),
    transcript TEXT,
    raw_extraction JSONB
);

-- Tools table
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    functionality TEXT,        -- what the tool does (2-3 sentences)
    problem_solved TEXT,       -- the specific problem it addresses for an AI practitioner
    tags TEXT[],
    first_seen_date DATE,
    source_video_ids UUID[],
    last_updated_at TIMESTAMPTZ DEFAULT now()
);

-- Junction: video <-> tools (many-to-many)
CREATE TABLE video_tools (
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    PRIMARY KEY (video_id, tool_id)
);

-- User interactions
CREATE TABLE user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    status TEXT CHECK (status IN ('to_explore', 'implemented', 'not_interested')) DEFAULT 'to_explore',
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Enforce one interaction record per tool
CREATE UNIQUE INDEX one_interaction_per_tool ON user_interactions(tool_id);
```

After running migrations, enable Row Level Security (RLS) in Supabase and add a policy that permits all operations when using the service key. The backend always uses the service key, so this is safe for a personal tool.

---

## Phase 2 — Backend

### 2.1 Initialise with uv

```bash
cd backend
uv init
uv add fastapi uvicorn supabase assemblyai anthropic yt-dlp python-telegram-bot pydantic-settings python-dotenv httpx
```

Never use `pip install`. All dependency changes go through `uv add`.

### 2.2 `db/client.py`

Initialise the Supabase client using `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` from the environment. Export a single `supabase` client instance to be imported by all other modules.

### 2.3 `services/downloader.py`

Use `yt-dlp` to download only the audio stream from an Instagram Reel URL. Save to a temp directory created with `tempfile.mkdtemp()`. Return the local file path and the video upload date (available in yt-dlp metadata as `upload_date`, format `YYYYMMDD`). Handle errors gracefully — if the URL is invalid or the post is private, raise a descriptive exception.

yt-dlp options:
- Format: `bestaudio/best`
- Quiet: True, No-warnings: True
- Extract flat: False
- Write info json: False — parse metadata from the info dict returned in-memory

### 2.4 `services/transcriber.py`

Use the AssemblyAI Python SDK (`aai.Transcriber` with default settings) to transcribe a local audio file. Return the plain text transcript. Clean up the temp audio file after transcription in a `try/finally` block regardless of success or failure.

### 2.5 `services/extractor.py`

Call the Claude API with the transcript as input. The system prompt must instruct Claude to:

1. Identify all distinct AI tools or AI-related product upgrades mentioned in the transcript.
2. For each tool, return a JSON array where each object has:
   - `name` — clean proper name (e.g. "e2b.dev", "21st.dev", "Claude Code")
   - `functionality` — 2–3 sentences describing what the tool does
   - `problem_solved` — 1–2 sentences describing the specific problem this tool solves for a developer or AI practitioner. Be concrete and outcome-focused. Good examples:
     - "Isolates AI agents in secure sandboxed environments so they cannot affect the host machine or other processes."
     - "Prevents AI-generated UI from looking generic by providing pre-built, design-quality components agents can reference."
     - "Eliminates boilerplate RAG pipeline setup by providing a fully managed retrieval and embedding layer."
   - `tags` — array from: `coding`, `claude code`, `image generation`, `video generation`, `audio`, `productivity`, `agents`, `rag`, `search`, `multimodal`, `harness engineering`, `data`, `devtools` — assign as many as relevant
3. Return **only** valid JSON. No markdown fences, no preamble.

If JSON parsing fails, retry once with an explicit "return only raw JSON" instruction appended. If it fails again, raise an exception including the raw response for debugging.

### 2.6 `services/deduplicator.py`

Implement `upsert_tools(tools: list, video_id: str, video_date: date) -> list[str]` with the following logic per tool:

**A. Check for existing record**
Query the `tools` table using a case-insensitive name match (`ilike`).

**B. Not found → insert**
Insert all fields: `name`, `functionality`, `problem_solved`, `tags`, `first_seen_date = video_date`, `source_video_ids = [video_id]`.

**C. Found → smart update via Claude**
Do not blindly overwrite existing data. Call the Claude API to compare existing vs. new data:

```
You are comparing two descriptions of the same tool to decide whether an update is warranted.

Existing record:
- functionality: {existing.functionality}
- problem_solved: {existing.problem_solved}
- tags: {existing.tags}

New extraction from a recent video:
- functionality: {new.functionality}
- problem_solved: {new.problem_solved}
- tags: {new.tags}

Respond ONLY with a JSON object:
{
  "should_update_functionality": true/false,
  "should_update_problem_solved": true/false,
  "should_update_tags": true/false,
  "merged_functionality": "...",
  "merged_problem_solved": "...",
  "merged_tags": [...]
}

Rules:
- Set should_update_* to true only if the new version adds genuinely new information absent from the existing version.
- Rephrasing of the same information is NOT a reason to update.
- merged_* fields must always be populated: use the best merged version if updating, or repeat the existing value if not.
- merged_tags is always the union of both tag sets.
```

Apply only fields where `should_update_*` is true. Always update `first_seen_date` to `min(existing, video_date)`, append `video_id` to `source_video_ids` if not already present, and touch `last_updated_at` if any field changed.

**D. Always after insert or update:**
- Upsert into `user_interactions` with `status = 'to_explore'` using ON CONFLICT DO NOTHING (preserves existing user status)
- Insert into `video_tools` using ON CONFLICT DO NOTHING

**E.** Return list of tool IDs processed.

### 2.7 Pre-flight diagnostics — `routers/diagnostics.py` + `services/assemblyai_check.py`

Before running the full ingest pipeline, validate AssemblyAI in isolation:

- `GET /api/diagnostics/assemblyai` — calls AssemblyAI transcript list API (`limit=1`) with `Authorization: <ASSEMBLYAI_API_KEY>`. Returns structured JSON: `ok`, `service`, `configured`, `reachable`, `http_status`, `message`, `hint`. Never echoes the key.
- `GET /api/diagnostics/summary` — ordered checklist (`steps[]`, `all_ok`, `next_if_all_ok`) for future checks (e.g. Supabase ping).

**Workflow:** health → `/api/diagnostics/assemblyai` (must be `"ok": true`) → `POST /api/webhook/reel`.

Env: `ASSEMBLYAI_API_KEY` is trimmed; surrounding single/double quotes from `.env` are stripped in `config.py` to avoid subtle 401s.

### 2.8 `routers/webhook.py`

`POST /api/webhook/reel`

Request body:
```json
{
  "url": "https://www.instagram.com/reel/...",
  "secret": "your_webhook_secret"
}
```

Steps:
1. Validate `secret` against `WEBHOOK_SECRET` env var — return 401 if mismatch.
2. Check if `url` already exists in `videos` — return `{"status": "already_processed"}` with 200 if so.
3. Return `{"status": "processing"}` immediately and hand off to a `BackgroundTasks` function.
4. In the background: call downloader → insert video row → transcriber → update transcript → extractor → update raw_extraction → deduplicator → update tool references.

### 2.9 `routers/tools.py`

- `GET /api/tools` — return tools joined with `user_interactions` status. Query `?status=to_explore|implemented|not_interested|all` (default: `all`). Sort by `first_seen_date` descending. Response headers: `Cache-Control: no-store` (avoids stale PWA caches).
- `GET /api/tools/counts` — `{ to_explore, implemented, not_interested, all }` for tab badges (always global counts).
- `GET /api/tools/tags` — sorted list of distinct tag strings from all tools (for filter UI).
- `PATCH /api/tools/{tool_id}/interaction` — update `status` and optional `notes`. Touch `updated_at`.

### 2.9a `routers/metrics.py`

- `GET /api/metrics/overview` — dashboard payload. Headers: `Cache-Control: no-store`.
- **`videos_last_7d`** — count of distinct reels with `processed_at >= now - 7 days` (rolling, UTC).
- **`tool_mentions_last_7d`** — count of **`video_tools` rows** (video↔tool links) where the video is in that same recent set. Same tool in two reels ⇒ two mentions.
- **`distinct_tools_in_new_reels_7d`** — distinct `tool_id` among those links.
- **`tools_first_seen_last_7d`** — tools whose **`first_seen_date` (DATE) ≥ `cutoff.date()`** where `cutoff = now - 7 days`, aligned with the reel rolling window. Older tools can still get new mentions without incrementing this.
- **`tag_prevalence`** — top 15 `{tag, count}` across all tools.
- **`status_breakdown`**, **`implemented_pct`**, **`series_last_7d`** — last field: 7 UTC **calendar** days (inclusive) with per-day `videos_processed` and `distinct_tools_linked` for reels processed that day.

### 2.10 `routers/videos.py`

- `GET /api/videos` — all videos with associated tool names via `video_tools`. Sort by `video_created_at` descending.
- `GET /api/videos/{video_id}` — single video with full tool details.

### 2.11 `main.py`

- FastAPI app with all routers under `/api` prefix
- CORS middleware allowing all origins (personal tool, multiple devices)
- `GET /health` returning `{"status": "ok"}`
- Env vars loaded via `pydantic-settings`

### 2.12 Telegram Bot — `services/telegram_bot.py`

Runs as a separate process (separate Railway service or alongside FastAPI via asyncio). The bot:
- Listens to a private group or channel
- Detects Instagram Reel URLs via regex on `instagram.com/reel/`
- POSTs the URL to `/api/webhook/reel` with `WEBHOOK_SECRET`
- Replies in chat with the processing result

---

## Phase 3 — Frontend

### 3.1 Initialise

```bash
cd frontend
npx create-vite@latest . --template react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install axios react-router-dom
```

### 3.2 Design Requirements

- Mobile-first, responsive — must look clean on iPhone Safari
- Tailwind utility classes only, no external component libraries
- Color scheme: `gray-950` background, `gray-900` cards, `violet-500` accent

### 3.3 Feed Page (`pages/Feed.jsx`)

- Fetch list from `GET /api/tools` with `params: { status: activeTab }` — **one row per tool** (Supabase `tools.id`), not per extraction.
- Fetch tab counts from `GET /api/tools/counts` (not derived from the filtered list)
- Optional tag filter: load `GET /api/tools/tags`, client-side filter current list (**any** selected tag matches)
- After status change: remove tool from list when it no longer matches `activeTab`; refresh counts
- **Cards | Table** toggle (persisted in `localStorage` key `ai-tools-tracker-feed-view`). Table: `components/ToolsTable.jsx` with status `<select>` and PATCH on change.
- FilterTabs + tag chips + ToolCard grid **or** table
- Empty state when no results or tag filter excludes everything

### 3.4 ToolCard Component (`components/ToolCard.jsx`)

Each card displays:
- Tool name (bold, large)
- First seen date (small, muted)
- `functionality` description
- `problem_solved` — visually distinct from functionality, e.g. prefixed with "Solves:" in a lighter or italicised style. This is the primary value-add field for quick scanning.
- Tags as small violet pill badges
- Action buttons: ✅ **Mark Implemented** / 🚫 **Not Interested** / 🔖 **To Explore** (reset, shown when status is not `to_explore`)
- Optimistic local state update on button click before API response
- "Seen in N video(s)" indicator

### 3.5 VideoDetail Page (`pages/VideoDetail.jsx`)

- Route: `/videos/:id`
- Shows Instagram URL (clickable), date, collapsed transcript (toggle to expand), and all tools with status badges

### 3.6 Routing

```
/ → Feed (tools library)
/dashboard → Dashboard (metrics overview)
/videos/:id → VideoDetail
```

Header nav: **Overview** (`/dashboard`), **Tools** (`/`).

### 3.7 Dashboard (`pages/Dashboard.jsx`)

- Fetches `GET /api/metrics/overview` once; neutral KPI stat cards (single accent), tag prevalence + triage bars (restrained palette), 7-day series as **two labeled rows** (reels vs tools linked) with a compact legend. Copy on cards explains mentions vs `first_seen_date`.

---

## Phase 4 — iOS Shortcut

Write these instructions into the README (do not code them — this is a manual setup step for the user):

1. Open the Shortcuts app → create a new shortcut named "Track AI Reels"
2. Tap the first block → set **Receive** input type to **URLs**, source to **Share Sheet**. If there's no input: **Continue**.
3. Add action: **Get Shortcut Input**
4. Add action: **Get Contents of URL**
   - URL: `https://your-railway-backend.up.railway.app/api/webhook/reel`
   - Method: POST
   - Request Body: JSON
   - Add field (Text) → key: `url`, value: **Shortcut Input** variable
   - Add field (Text) → key: `secret`, value: your webhook secret
5. Add action: **Show Content**
6. Tap the shortcut name → Details → enable **Show in Share Sheet**

The shortcut appears in Instagram's native share sheet. One tap submits the Reel URL to the backend.

---

## Phase 5 — Deployment

### Backend → Railway

```
# backend/Procfile
web: uv run uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set all env vars in the Railway dashboard. Railway auto-detects `pyproject.toml`.

### Frontend → Vercel

Set `VITE_API_BASE_URL` to the Railway backend URL in Vercel environment settings. Build command: `npm run build`. Output directory: `dist`.

---

## Build Order

Pause and confirm with the user after each step:

1. Create IDE context files (`CLAUDE.md`, `.cursor/rules/ai-tools-tracker.mdc`)
2. Schema — run `001_initial.sql` in Supabase
3. Backend services — downloader → transcriber → extractor → deduplicator
4. Backend routers — webhook → tools → videos
5. Backend smoke test — submit a real Reel URL via `curl`, verify tools appear in DB
6. Frontend — Feed → ToolCard → FilterTabs → VideoDetail
7. Frontend smoke test — run locally against local backend
8. Deployment — Railway then Vercel
9. README — write iOS Shortcut instructions
10. Telegram bot — implement and test

---

## Constraints and Non-Negotiables

- Always use `uv add` for packages, never `pip install`
- Always use `uv run` to execute Python locally
- Never hardcode secrets — always read from environment variables
- Webhook must be idempotent — duplicate URL submissions must be silently ignored
- User interaction status must survive re-processing of the same video
- Tool records must never be blindly overwritten — always run the Claude comparison first
- All API responses must be JSON
- All dates must be ISO 8601 strings (`YYYY-MM-DD`)
- Frontend must handle loading, error, and empty states on every data fetch

---

## Definition of Done

- [ ] IDE context files created (`CLAUDE.md` and `.cursor/rules/ai-tools-tracker.mdc`)
- [ ] A real Instagram Reel URL submitted to `POST /api/webhook/reel` results in tools in the DB
- [ ] Each tool has `functionality` and `problem_solved` populated
- [ ] Feed page shows tools with correct status filtering on mobile and desktop
- [ ] ToolCard displays `problem_solved` visually distinct from `functionality`
- [ ] Status changes (Implemented / Not Interested) persist across page refresh
- [ ] iOS Shortcut submits a URL directly from Instagram's share sheet
- [ ] Duplicate URL submissions return `already_processed` without side effects
- [ ] Two videos referencing the same tool produce one tool row with the earliest date
- [ ] Re-processing a known tool only updates fields when Claude detects genuinely new information
