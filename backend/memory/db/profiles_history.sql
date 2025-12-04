CREATE TABLE profiles_history (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  project_id TEXT NULL,
  version INT NOT NULL,
  profile_json JSONB NOT NULL,
  extra_metadata JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_profiles_history_user_project
  ON profiles_history(user_id, project_id, version DESC);