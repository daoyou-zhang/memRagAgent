CREATE TABLE conversation_messages (
    id              BIGSERIAL PRIMARY KEY,          -- 递增 message_id，方便按范围选
    session_id      VARCHAR(128) NOT NULL,          -- 关联 conversation_sessions.session_id

    user_id         VARCHAR(64),                    -- 冗余字段，方便按 user 查
    agent_id        VARCHAR(64),                    -- 冗余字段，方便按 agent 查
    project_id      VARCHAR(128),                   -- 冗余字段，方便按 project 查

    role            VARCHAR(16) NOT NULL,           -- 'user' | 'assistant' | 'system' | 'tool'
    content         TEXT NOT NULL,
    metadata        JSONB,                          -- 补充信息：渠道、消息 ID、调用来源等

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conv_messages_session_time
    ON conversation_messages (session_id, created_at);

CREATE INDEX idx_conv_messages_user_project
    ON conversation_messages (user_id, project_id);
