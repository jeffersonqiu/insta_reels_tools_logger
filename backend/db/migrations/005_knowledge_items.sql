-- Knowledge items (Project V2 Step 6). Schema-only and backward compatible:
-- adds one new table; no existing table, column or row is touched, so it is safe to
-- apply BEFORE the new backend is deployed. Idempotent. No LLM backfill here
-- (see backend/scripts/backfill_knowledge_items.py for the opt-in backfill).

CREATE TABLE IF NOT EXISTS knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL UNIQUE REFERENCES videos(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL DEFAULT 'instagram_reel',
    source_url TEXT NOT NULL,

    title TEXT,
    summary TEXT,

    key_ideas JSONB NOT NULL DEFAULT '[]'::jsonb,      -- ["idea", ...]
    repositories JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{"name","url","description"}, ...]
    concepts JSONB NOT NULL DEFAULT '[]'::jsonb,       -- ["concept", ...]
    action_items JSONB NOT NULL DEFAULT '[]'::jsonb,   -- ["action", ...]

    tags TEXT[] NOT NULL DEFAULT '{}',

    raw_extraction JSONB,                              -- full KnowledgeExtraction payload (incl. tools)

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_items_created_at_idx ON knowledge_items (created_at DESC);

-- Backend uses the service key (bypasses RLS); enabling RLS with no policies blocks anon access.
ALTER TABLE knowledge_items ENABLE ROW LEVEL SECURITY;
