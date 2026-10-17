# Project V2 Step 6: knowledge items

Each successfully processed Reel produces one `knowledge_items` row alongside the existing tool records. A Reel with no AI tools still produces knowledge. Source captions and transcripts remain on `videos`.

## Database schema

Migration: `backend/db/migrations/005_knowledge_items.sql`. It creates a table and an index, enables row security, and changes no existing data or tool relationships. It is safe to apply before deploying the new backend and to run again. It performs no LLM backfill.

| Column | Type | Rules/default |
| --- | --- | --- |
| `id` | UUID | Primary key; generated UUID |
| `video_id` | UUID | Required, unique; references `videos(id)` with cascade deletion |
| `source_type` | TEXT | Required; `instagram_reel` |
| `source_url` | TEXT | Required; canonical source URL |
| `title`, `summary` | TEXT | Nullable in storage |
| `key_ideas`, `repositories`, `concepts`, `action_items` | JSONB | Required; `[]` |
| `tags` | TEXT[] | Required; empty array |
| `raw_extraction` | JSONB | Full validated knowledge extraction, including tools |
| `created_at`, `updated_at` | TIMESTAMPTZ | Required; `now()` |

There is a descending index on `created_at`. The persistence service updates `updated_at` on every upsert while preserving the original `id` and `created_at`. RLS has no client policies; the backend's Supabase service key bypasses RLS.

## Extraction and processing

`KnowledgeExtraction` requires string `title` and `summary`. The following lists default to empty:

- `key_ideas`, `concepts`, `action_items`, `tags`: strings.
- `tools`: existing `ToolExtraction` objects (`name`, `functionality`, `problem_solved`, `tags`).
- `repositories`: objects with required `name` and optional `url` and `description`.

The prompt uses the current transcript and caption, preserves caption spelling for tool names, and instructs the model to leave repository URLs null unless the source explicitly supplies a URL. It retries invalid JSON or schema output once. No vision, OCR, or new transcription service is introduced.

Processing saves the knowledge item with an upsert on `video_id`, then calls the existing tool deduplicator. It marks the video completed only after extraction, knowledge persistence, and tool handling succeed. A failure remains recorded on the durable video row; a retry updates the same item. An item may exist while its source video is failed if tool handling failed after item persistence; clients can inspect source status through the detail endpoint.

`videos.raw_extraction` retains its legacy tool-list shape. `tools`, `video_tools`, smart tool merging, and existing interaction statuses/notes keep their existing behavior. The legacy `extract_tools_from_transcript` helper still returns tool models.

## Read APIs

- `GET /api/items`: JSON list ordered by `created_at` descending. Optional `limit` defaults to 50 and must be between 1 and 200. Empty databases return `[]`.
- `GET /api/items/{id}`: `{ "item": {...}, "video": {...} }`. Video fields: `id`, `instagram_url`, `caption`, `transcript`, `video_created_at`, `status`. A missing UUID returns 404; a malformed UUID returns 422 before querying the database.

Both successful responses disable caching. No frontend changes are required.

## Production rollout: migration before merge

1. Keep application changes on `feat/knowledge-items`. Do not merge or deploy them until the production migration is confirmed.
2. Open the **production Supabase project**. Open **SQL Editor → New query**.
3. Paste the entire contents of `backend/db/migrations/005_knowledge_items.sql` and run it as the project owner/Postgres role. Migrations 001–004 must already exist. Run only 005 for this existing installation.
4. Run the entire read-only file `backend/db/verification/005_knowledge_items.sql`. Its first result must have **eight checks, all true**. The next result lists the expected **14 columns** and their defaults. The duplicate-video query must return zero rows. An empty knowledge-items table is expected until new processing or a deliberate backfill occurs.
5. Confirm that the production migration and verification succeeded before merging the feature branch into `master`. A local migration check does not establish that production has been migrated.
6. After the authorized merge, confirm `origin/master` contains the feature commit and allow Railway to deploy it.
7. Verify `GET /health` (200), `GET /health/db` (`{"status":"ok","database":"ok"}`), and `GET /api/items` (200 and a JSON list) on `https://instareelstoolslogger-production.up.railway.app`.

Do not submit a Reel merely to verify deployment while the known Instagram authentication issue remains. Do not run the backfill as part of deployment.

## Optional historical backfill

Completed historical videos may have no knowledge item. This is allowed. The opt-in script reads stored transcript/caption, skips videos with an existing knowledge item, and writes only knowledge items. It does not download audio, transcribe, or alter tools/interactions.

From `backend/`, using the intended database and credentials:

```sh
uv run python scripts/backfill_knowledge_items.py --dry-run
```

The dry run lists candidates without LLM calls or writes. Only if deliberately requested, run a bounded paid extraction:

```sh
uv run python scripts/backfill_knowledge_items.py --limit 3
```

The default limit is five; zero and negative limits are rejected before database access. This script is for low-volume historical data and uses the existing Supabase query row limits; it is not a bulk migration tool.

## Verification

Run the complete backend suite from `backend/`:

```sh
uv run pytest
```

Tests mock Anthropic, Instagram downloading, AssemblyAI transcription, and Supabase. A shared fixture forbids external network connections. Coverage includes extraction with/without tools, parse retries, item upserts/retries and failure states, actual tool persistence against a mock database, preservation of implemented/not-interested statuses and notes, legacy Tools/video endpoints, item endpoints/UUID validation, backfill cost controls, durable ingestion, and health checks.

Step 7 and the frontend are outside this change.
