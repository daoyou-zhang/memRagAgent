CREATE TABLE IF NOT EXISTS knowledge_documents (
    id              SERIAL PRIMARY KEY,
    collection_id   INTEGER             NOT NULL REFERENCES knowledge_collections(id) ON DELETE CASCADE,
    external_id     VARCHAR(128),       -- 原始系统中的标识，例如法条编号 / 文档 ID
    title           VARCHAR(512)        NOT NULL,
    source_uri      TEXT,               -- 文件路径或 URL
    metadata        JSONB,
    status          VARCHAR(32)         NOT NULL DEFAULT 'raw', -- raw / parsed / indexed
    created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_collection
    ON knowledge_documents (collection_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_status
    ON knowledge_documents (status);
