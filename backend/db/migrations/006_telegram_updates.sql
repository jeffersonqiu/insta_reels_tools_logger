-- Step 9: deduplicate Telegram deliveries before paid Q&A or Reel submission.
-- Metadata only: no message text, chat ID, user ID, or credentials are stored.
CREATE TABLE IF NOT EXISTS telegram_updates (
    update_id BIGINT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'processing'
        CHECK (status IN ('processing', 'completed', 'failed')),
    error_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
ALTER TABLE telegram_updates ENABLE ROW LEVEL SECURITY;
