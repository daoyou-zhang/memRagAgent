CREATE TABLE memory_generation_jobs (
    id               BIGSERIAL PRIMARY KEY,

    user_id          VARCHAR(64),
    agent_id         VARCHAR(64),
    project_id       VARCHAR(128),

    session_id       VARCHAR(128) NOT NULL,      -- 针对哪个会话生成记忆

    -- 本次 job 要处理的消息范围（两种方式二选一，用其一即可）：
    start_message_id BIGINT,                     -- 针对 [start_message_id, end_message_id] 这一段
    end_message_id   BIGINT,
    -- 或者使用时间范围：
    start_time       TIMESTAMPTZ,
    end_time         TIMESTAMPTZ,

    job_type         VARCHAR(32) NOT NULL,       -- 例如：'episodic_summary' | 后续可扩展 'semantic_extract'
    target_types     JSONB NOT NULL,             -- 例如：['episodic']，为将来多类型预留

    status           VARCHAR(32) NOT NULL DEFAULT 'pending',  -- 'pending' | 'running' | 'done' | 'failed'
    error_message    TEXT,                        -- 失败原因（若有）

    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mem_jobs_status
    ON memory_generation_jobs (status);

CREATE INDEX idx_mem_jobs_session
    ON memory_generation_jobs (session_id, created_at);
