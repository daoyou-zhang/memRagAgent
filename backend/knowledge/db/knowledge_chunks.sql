CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER             NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER             NOT NULL,
    section_label   VARCHAR(256),       -- 例如 "第三章 第十条"、"第 3 段"
    text            TEXT                NOT NULL,
    tags            JSONB,              -- 通用标签：主题、适用范围、学科等
    embedding       JSONB,              -- 暂用 JSONB 存储向量数组，后续可切换 pgvector
    importance      FLOAT               DEFAULT 0.5,
    metadata        JSONB,
    created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document
    ON knowledge_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_chunk_index
    ON knowledge_chunks (document_id, chunk_index);
