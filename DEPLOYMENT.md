# Deployment checklist — Railway (API) + Vercel (UI) + iOS Shortcut

Use this after local smoke tests pass (`/health`, `/api/diagnostics/assemblyai`, webhook → tools in Supabase).

**When you add API routes** (e.g. `/api/metrics/overview`), deploy **Railway (backend) before or together with** Vercel so the UI does not call missing endpoints.

**Dashboard KPI semantics** (so you do not confuse counts with Supabase row counts): *Mentions* = rows in `video_tools` for reels ingested in the rolling 7d window. *Tools first logged* = tools whose `first_seen_date` is on or after the same rolling cutoff date. See `CLAUDE.md` §2.9a for full definitions.

---

## Part 1 — Railway (FastAPI backend)

### Why Railpack fails on first import

If you see **`Railpack could not determine how to build the app`** and the log lists **`backend/`**, **`frontend/`**, and docs at the repo root, Railway is building from the **monorepo root** with **Railpack** — it does not see a single Node/Python app there.

**Fix (pick one):**

| Approach | Root directory (service setting) | Docker image |
|----------|----------------------------------|--------------|
| **A — Recommended** | **Leave empty** (repo root) | Uses **`Dockerfile`** at repo root (builds `backend/`) |
| **B — Alternate** | **`backend`** | Uses **`backend/Dockerfile`** (context = `backend/`) |

After **git pull** of the latest repo, **Option A** is the simplest: do **not** set a root directory, redeploy — Railway should detect the root **`Dockerfile`** and build with Docker ([docs](https://docs.railway.com/builds/dockerfiles)).

### 1.1 Create the service

1. Go to [railway.app](https://railway.app) → sign in (GitHub is fine).
2. **New project** → **Deploy from GitHub repo** → pick `insta_reels_tools_logger` (or your fork).
3. Railway creates a service. Open it → **Settings**.

### 1.2 Configure the build (important)

**Option A — Repo root (recommended)**

1. **Settings** → find **Root Directory** / **Watch paths** (wording varies).
2. **Clear** “Root directory” if it is set to anything — the service should use the **full repo** so the root **`Dockerfile`** is present.
3. **Settings** → **Build** → set **Builder** to **Dockerfile** if Railpack is still selected.
4. **Dockerfile path**: `Dockerfile` (file at repository root, next to `backend/`).

**Option B — `backend` only**

1. **Root Directory** = **`backend`**.
2. **Builder** = **Dockerfile**.
3. **Dockerfile path** = **`Dockerfile`** (this is `backend/Dockerfile` on disk).

### 1.3 Environment variables

In the service → **Variables** → add (same values as local `backend/.env`):

| Name | Notes |
|------|--------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | **Service role** secret (`sb_secret_...`), not anon |
| `ASSEMBLYAI_API_KEY` | AssemblyAI dashboard |
| `ANTHROPIC_API_KEY` | Anthropic |
| `WEBHOOK_SECRET` | **You choose**; must match iOS Shortcut `secret` |
| `TELEGRAM_BOT_TOKEN` | Optional; leave empty if unused |

Optional later:

| Name | Notes |
|------|--------|
| `CORS_ALLOW_ORIGINS` | Not wired in code yet; CORS is `*` in v1 |

Redeploy after saving variables.

### 1.3b `start.sh not found`

That message is harmless if the **Dockerfile** `CMD` runs **uvicorn**. It often appears when Railpack was tried first; switching to **Dockerfile** builder removes the need for `start.sh`.

### 1.4 Public URL

1. Service → **Settings** → **Networking** → **Generate domain** (or add custom domain).
2. Copy the HTTPS base URL, e.g. `https://your-service.up.railway.app`  
   **No trailing slash** when you paste into Vercel.

### 1.5 Verify backend live

Replace `BASE` with your Railway URL:

```bash
curl -s "$BASE/health"
# expect: {"status":"ok"}

curl -s "$BASE/api/diagnostics/assemblyai" | python3 -m json.tool
# expect: "ok": true

curl -s -X POST "$BASE/api/webhook/reel" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.instagram.com/reel/SHORTCODE/","secret":"YOUR_WEBHOOK_SECRET"}'
# expect: {"status":"processing"} or already_processed
```

---

## Part 2 — Vercel (React frontend)

### 2.1 Import project

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project** → import the same GitHub repo.

### 2.2 Configure the app

1. **Root Directory**: `frontend`  
2. **Framework Preset**: Vite (auto-detected).
3. **Build Command**: `npm run build` (default).
4. **Output Directory**: `dist` (Vite default).

### 2.3 Environment variable (required)

**Settings** → **Environment Variables** (Production + Preview if you want):

| Name | Value |
|------|--------|
| `VITE_API_BASE_URL` | `https://your-service.up.railway.app` |

- **No** trailing slash.
- Must be the **exact** Railway HTTPS origin your browser will call (CORS is open in v1, but wrong host = wrong API).

Redeploy after adding the variable (or trigger a new deployment).

### 2.4 Verify UI

1. Open the Vercel URL.
2. Feed should load tools (same Supabase as backend).
3. **Watch Reel** should open Instagram in a new tab.

---

## Part 3 — iOS Shortcut (Share Sheet → webhook)

1. **Shortcuts** → **+** → name it e.g. `Track AI Reels`.
2. First block: **Receive** … **URLs** from **Share Sheet**; **Allow Running When Not Connected** optional.
3. Add **Get Shortcut Input** (or use provided URL from share sheet).
4. Add **Get Contents of URL**:
   - **URL**: `https://your-service.up.railway.app/api/webhook/reel`
   - **Method**: POST
   - **Request Body**: JSON
   - **Add new field** `url` → map to **Shortcut Input** (the shared Reel link).
   - **Add new field** `secret` → type your **`WEBHOOK_SECRET`** (same as Railway).
5. Add **Show Result** or **Show Notification** so you see `processing` / `already_processed` / errors.
6. Shortcut details → **Show in Share Sheet** → enable.

**Test:** Open Instagram → share a Reel → your shortcut → confirm `processing`, then check Supabase / Vercel feed.

---

## Part 4 — Optional cleanups

- **Duplicate Reel URLs:** `videos.instagram_url` is unique on the full string; prefer always posting the **canonical** URL (e.g. strip `?igsh=` if you want one row per reel).
- **Tighten CORS:** Later, set `allow_origins` in `main.py` to your Vercel domain only.
- **Railway sleep / limits:** Free tier may sleep; first request after idle can be slow.

---

## Quick reference

| Piece | URL / command |
|-------|----------------|
| Health | `GET https://<railway>/health` |
| Webhook | `POST https://<railway>/api/webhook/reel` |
| Frontend env | `VITE_API_BASE_URL=https://<railway>` |

If anything fails, check **Railway deploy logs** (build + runtime) and **browser DevTools → Network** on the Vercel site for the failing request host.
