CREATE TABLE memory_embeddings (
  id          SERIAL PRIMARY KEY,
  memory_id   INT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  embedding   JSONB NOT NULL,
  model_name  TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_memory_embeddings_memory_model
  ON memory_embeddings(memory_id, model_name);
