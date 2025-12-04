CREATE TABLE conversation_sessions (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(128) NOT NULL UNIQUE,  -- 业务侧自定义的会话 ID（可与外部系统对齐）

    user_id         VARCHAR(64),                   -- 哪个用户
    agent_id        VARCHAR(64),                   -- 哪个 Agent（可空）
    project_id      VARCHAR(128),                  -- 哪个项目

    title           VARCHAR(256),                  -- 会话标题（可选）
    status          VARCHAR(32) NOT NULL DEFAULT 'active',  -- 'active' | 'closed'

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at       TIMESTAMPTZ                     -- 会话结束时间（触发 episodic 的一个依据）
);

CREATE INDEX idx_conv_sessions_user_project
    ON conversation_sessions (user_id, project_id);

CREATE INDEX idx_conv_sessions_status
    ON conversation_sessions (status);

ALTER TABLE conversation_sessions
  ADD COLUMN auto_episodic_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN auto_semantic_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN auto_profile_enabled  BOOLEAN NOT NULL DEFAULT FALSE;
