-- ============================================================
-- memRagAgent 数据库完整初始化脚本
-- 执行顺序: 基础表 → 租户表 → 业务表 → 索引
-- ============================================================

-- ============================================================
-- 1. 创建扩展
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 2. 基础业务表（无外键依赖）
-- ============================================================

-- 记忆表
CREATE TABLE IF NOT EXISTS memories (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(128) NOT NULL,
    project_id      VARCHAR(128),
    session_id      VARCHAR(128),
    type            VARCHAR(32) NOT NULL DEFAULT 'episodic',
    content         TEXT NOT NULL,
    context         JSONB,
    importance      FLOAT DEFAULT 0.5,
    access_count    INTEGER DEFAULT 0,
    last_accessed   TIMESTAMPTZ DEFAULT NOW(),
    tags            JSONB,
    embedding       JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS ix_memories_project ON memories(project_id);
CREATE INDEX IF NOT EXISTS ix_memories_session ON memories(session_id);
CREATE INDEX IF NOT EXISTS ix_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS ix_memories_created ON memories(created_at);

-- 用户画像表
CREATE TABLE IF NOT EXISTS profiles (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(128) NOT NULL UNIQUE,
    project_id      VARCHAR(128),
    display_name    VARCHAR(128),
    core_identity   JSONB,
    personality     JSONB,
    beliefs_values  JSONB,
    goals_motivations JSONB,
    knowledge_skills JSONB,
    interaction_style JSONB,
    dynamic_state   JSONB,
    raw_profile     TEXT,
    version         INTEGER DEFAULT 1,
    last_memory_id  INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_profiles_user ON profiles(user_id);
CREATE INDEX IF NOT EXISTS ix_profiles_project ON profiles(project_id);

-- 会话表
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(128) NOT NULL UNIQUE,
    user_id         VARCHAR(128) NOT NULL,
    project_id      VARCHAR(128),
    title           VARCHAR(256),
    status          VARCHAR(32) DEFAULT 'active',
    summary         TEXT,
    metadata        JSONB,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sessions_session ON conversation_sessions(session_id);
CREATE INDEX IF NOT EXISTS ix_sessions_user ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_project ON conversation_sessions(project_id);

-- 消息表
CREATE TABLE IF NOT EXISTS conversation_messages (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(128) NOT NULL,
    role            VARCHAR(32) NOT NULL,
    content         TEXT NOT NULL,
    content_type    VARCHAR(32) DEFAULT 'text',
    metadata        JSONB,
    token_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_messages_session ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS ix_messages_role ON conversation_messages(role);
CREATE INDEX IF NOT EXISTS ix_messages_created ON conversation_messages(created_at);

-- 记忆嵌入表
CREATE TABLE IF NOT EXISTS memory_embeddings (
    id              SERIAL PRIMARY KEY,
    memory_id       INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    embedding       JSONB NOT NULL,
    model_name      VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(memory_id)
);

CREATE INDEX IF NOT EXISTS ix_memory_embeddings_memory ON memory_embeddings(memory_id);

-- 记忆生成任务表
CREATE TABLE IF NOT EXISTS memory_generation_jobs (
    id              SERIAL PRIMARY KEY,
    job_type        VARCHAR(32) NOT NULL,
    user_id         VARCHAR(128) NOT NULL,
    project_id      VARCHAR(128),
    status          VARCHAR(32) DEFAULT 'pending',
    input_params    JSONB,
    result          JSONB,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_jobs_user ON memory_generation_jobs(user_id);
CREATE INDEX IF NOT EXISTS ix_jobs_status ON memory_generation_jobs(status);

-- ============================================================
-- 3. 租户相关表
-- ============================================================

-- 租户表
CREATE TABLE IF NOT EXISTS tenants (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(64) NOT NULL UNIQUE,
    name            VARCHAR(128) NOT NULL,
    type            VARCHAR(32) DEFAULT 'personal',
    status          VARCHAR(32) DEFAULT 'active',
    config          JSONB,
    max_users       INTEGER DEFAULT 10,
    max_storage_mb  INTEGER DEFAULT 1000,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tenants_code ON tenants(code);
CREATE INDEX IF NOT EXISTS ix_tenants_status ON tenants(status);

-- 用户组表
CREATE TABLE IF NOT EXISTS user_groups (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code            VARCHAR(64) NOT NULL,
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    is_default      BOOLEAN DEFAULT FALSE,
    config          JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS ix_user_groups_tenant ON user_groups(tenant_id);
CREATE INDEX IF NOT EXISTS ix_user_groups_default ON user_groups(tenant_id, is_default);

-- 租户用户表（避免与其他项目 users 表冲突）
CREATE TABLE IF NOT EXISTS tenant_users (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    group_id        INTEGER REFERENCES user_groups(id) ON DELETE SET NULL,
    username        VARCHAR(64) NOT NULL,
    email           VARCHAR(128),
    display_name    VARCHAR(128),
    password_hash   VARCHAR(256),
    external_id     VARCHAR(128),
    role            VARCHAR(32) DEFAULT 'member',
    status          VARCHAR(32) DEFAULT 'active',
    config          JSONB,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_tenant_users_username ON tenant_users(tenant_id, username);
CREATE INDEX IF NOT EXISTS ix_tenant_users_tenant ON tenant_users(tenant_id);
CREATE INDEX IF NOT EXISTS ix_tenant_users_email ON tenant_users(tenant_id, email);
CREATE INDEX IF NOT EXISTS ix_tenant_users_external ON tenant_users(tenant_id, external_id);
CREATE INDEX IF NOT EXISTS ix_tenant_users_role ON tenant_users(tenant_id, role);

-- API 密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         INTEGER REFERENCES tenant_users(id) ON DELETE CASCADE,
    name            VARCHAR(128) NOT NULL,
    key_prefix      VARCHAR(16) NOT NULL,
    key_hash        VARCHAR(256) NOT NULL UNIQUE,
    scopes          JSONB,
    status          VARCHAR(32) DEFAULT 'active',
    expires_at      TIMESTAMPTZ,
    last_used_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS ix_api_keys_user ON api_keys(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS ix_api_keys_hash ON api_keys(key_hash);

-- ============================================================
-- 4. 为现有表添加 tenant_id（可选）
-- ============================================================

ALTER TABLE memories ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_memories_tenant ON memories(tenant_id);

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_profiles_tenant ON profiles(tenant_id);

ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_sessions_tenant ON conversation_sessions(tenant_id);

ALTER TABLE memory_generation_jobs ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_jobs_tenant ON memory_generation_jobs(tenant_id);

-- ============================================================
-- 5. 初始化默认租户
-- ============================================================

INSERT INTO tenants (code, name, type, status, max_users, max_storage_mb)
VALUES ('default', '默认租户', 'personal', 'active', 100, 10000)
ON CONFLICT (code) DO NOTHING;

-- 为默认租户创建默认用户组
INSERT INTO user_groups (tenant_id, code, name, is_default)
SELECT id, 'default', '默认组', TRUE
FROM tenants WHERE code = 'default'
ON CONFLICT (tenant_id, code) DO NOTHING;

-- ============================================================
-- 完成
-- ============================================================
SELECT 'Memory 数据库初始化完成' AS status;
