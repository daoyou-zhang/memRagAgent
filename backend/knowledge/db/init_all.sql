-- ============================================================
-- Knowledge 数据库完整初始化脚本
-- ============================================================

-- 知识集合表
CREATE TABLE IF NOT EXISTS knowledge_collections (
    id              SERIAL PRIMARY KEY,
    project_id      VARCHAR(128),
    name            VARCHAR(256) NOT NULL,
    domain          VARCHAR(64) NOT NULL,
    description     TEXT,
    default_language VARCHAR(16) DEFAULT 'zh-CN',
    status          VARCHAR(32) DEFAULT 'active',
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_collections_project ON knowledge_collections(project_id);
CREATE INDEX IF NOT EXISTS ix_collections_domain ON knowledge_collections(domain);
CREATE INDEX IF NOT EXISTS ix_collections_status ON knowledge_collections(status);

-- 知识文档表
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id              SERIAL PRIMARY KEY,
    collection_id   INTEGER NOT NULL REFERENCES knowledge_collections(id) ON DELETE CASCADE,
    external_id     VARCHAR(256),
    title           VARCHAR(512) NOT NULL,
    source_uri      TEXT,
    source_type     VARCHAR(64),
    status          VARCHAR(32) DEFAULT 'pending',
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_documents_collection ON knowledge_documents(collection_id);
CREATE INDEX IF NOT EXISTS ix_documents_external ON knowledge_documents(external_id);
CREATE INDEX IF NOT EXISTS ix_documents_status ON knowledge_documents(status);

-- 知识分块表
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    section_label   VARCHAR(256),
    text            TEXT NOT NULL,
    tags            JSONB,
    embedding       JSONB,
    importance      FLOAT DEFAULT 0.5,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chunks_document ON knowledge_chunks(document_id);
CREATE INDEX IF NOT EXISTS ix_chunks_index ON knowledge_chunks(document_id, chunk_index);

-- ============================================================
-- 完成
-- ============================================================
SELECT 'Knowledge 数据库初始化完成' AS status;
