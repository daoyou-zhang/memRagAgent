-- profiles.sql
-- 用户画像表，存储基于 memories 聚合出的结构化画像 JSON

CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    project_id TEXT NULL,
    profile_json JSONB NOT NULL,
    extra_metadata JSONB NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_user_project
    ON profiles(user_id, project_id);
