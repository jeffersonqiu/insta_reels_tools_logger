-- Durable ingestion (Project V2 Step 5).
-- Additive and non-destructive: no rows are deleted, no existing columns are rewritten
-- (videos.instagram_url is left untouched). Safe to run BEFORE deploying the new backend:
-- the old backend ignores the new columns. Idempotent (safe to re-run).

ALTER TABLE videos ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS canonical_url TEXT;
-- processing_error already exists (002_processing_error.sql) and is reused.

-- Backfill status for pre-existing rows only (status IS NULL). Legacy rows were inserted
-- only after a successful download, so: error => failed, extraction present => completed,
-- anything else was interrupted mid-pipeline => failed.
UPDATE videos
SET status = CASE
        WHEN processing_error IS NOT NULL THEN 'failed'
        WHEN raw_extraction IS NOT NULL THEN 'completed'
        ELSE 'failed'
    END,
    completed_at = CASE
        WHEN processing_error IS NULL AND raw_extraction IS NOT NULL THEN processed_at
        ELSE NULL
    END,
    attempt_count = 1
WHERE status IS NULL;

-- Backfill canonical_url for legacy Instagram rows. Only the earliest row per shortcode
-- gets the value; later duplicates stay NULL so the unique index below can never fail
-- and no row needs deleting. Rows that don't match the pattern stay NULL.
WITH parsed AS (
    SELECT id,
           'https://www.instagram.com/reel/' ||
           substring(instagram_url from '^https?://(?:www\.)?instagram\.com/(?:[^/?#]+/)?(?:reels?|p)/([A-Za-z0-9_-]+)') || '/' AS canon,
           row_number() OVER (
               PARTITION BY substring(instagram_url from '^https?://(?:www\.)?instagram\.com/(?:[^/?#]+/)?(?:reels?|p)/([A-Za-z0-9_-]+)')
               ORDER BY processed_at, id
           ) AS rn
    FROM videos
    WHERE canonical_url IS NULL
      AND instagram_url ~ '^https?://(www\.)?instagram\.com/([^/?#]+/)?(reels?|p)/[A-Za-z0-9_-]+'
)
UPDATE videos v
SET canonical_url = p.canon
FROM parsed p
WHERE v.id = p.id AND p.rn = 1;

ALTER TABLE videos ALTER COLUMN status SET DEFAULT 'queued';
ALTER TABLE videos ALTER COLUMN status SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'videos_status_check') THEN
        ALTER TABLE videos
            ADD CONSTRAINT videos_status_check
            CHECK (status IN ('queued', 'processing', 'completed', 'failed'));
    END IF;
END $$;

-- Concurrency guard: one durable row per canonical Reel (multiple NULLs allowed).
CREATE UNIQUE INDEX IF NOT EXISTS videos_canonical_url_key ON videos (canonical_url);
