CREATE TABLE IF NOT EXISTS knowledge_collections (
    id              SERIAL PRIMARY KEY,
    project_id      VARCHAR(128),
    name            VARCHAR(256)        NOT NULL,
    domain          VARCHAR(64)         NOT NULL, -- 例如 law / psychology / sales_script / medical_terms
    description     TEXT,
    default_language VARCHAR(16),
    metadata        JSONB,
    created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_collections_project
    ON knowledge_collections (project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_collections_domain
    ON knowledge_collections (domain);
