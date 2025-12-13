CREATE TABLE memories (
    id              SERIAL PRIMARY KEY,          -- 你也可以改成 UUID
    user_id         VARCHAR(64),                -- 可空
    agent_id        VARCHAR(64),                -- 可空
    project_id      VARCHAR(128),               -- 可空

    type            VARCHAR(32) NOT NULL,       -- 'working' | 'episodic' | 'semantic'
    source          VARCHAR(32) NOT NULL,       -- 'user_input' | 'agent_output' | ...

    text            TEXT NOT NULL,              -- 主要内容（短，清晰）
    summary         TEXT,                       -- 可选摘要

    importance      REAL NOT NULL DEFAULT 0.5,  -- 0~1
    emotion         VARCHAR(32),                -- 'neutral' | 'positive' | ...

    tags            JSONB,                      -- 字符串数组，如 ["preference","answer_style"]
    metadata        JSONB,                      -- 任意补充信息

    -- 向量嵌入（合并自 memory_embeddings，减少 JOIN）
    embedding       JSONB,                      -- 向量数组，如 [0.1, 0.2, ...]
    embedding_model VARCHAR(64),                -- 向量模型名称

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_access_at  TIMESTAMPTZ,
    recall_count    INTEGER NOT NULL DEFAULT 0
);

-- 常用查询索引（可选）：
CREATE INDEX idx_memories_user_project
    ON memories (user_id, project_id);

CREATE INDEX idx_memories_type
    ON memories (type);

CREATE INDEX idx_memories_importance
    ON memories (importance DESC);

-- 如果用 JSONB：
CREATE INDEX idx_memories_tags_gin
    ON memories USING GIN (tags);

CREATE INDEX idx_memories_metadata_gin
    ON memories USING GIN (metadata);