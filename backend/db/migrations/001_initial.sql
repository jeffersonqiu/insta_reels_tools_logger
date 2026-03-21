CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instagram_url TEXT UNIQUE NOT NULL,
    video_created_at DATE,
    processed_at TIMESTAMPTZ DEFAULT now(),
    transcript TEXT,
    raw_extraction JSONB
);

CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    functionality TEXT,
    problem_solved TEXT,
    tags TEXT[],
    first_seen_date DATE,
    source_video_ids UUID[],
    last_updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS video_tools (
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    PRIMARY KEY (video_id, tool_id)
);

CREATE TABLE IF NOT EXISTS user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    status TEXT CHECK (status IN ('to_explore', 'implemented', 'not_interested')) DEFAULT 'to_explore',
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS one_interaction_per_tool ON user_interactions(tool_id);
