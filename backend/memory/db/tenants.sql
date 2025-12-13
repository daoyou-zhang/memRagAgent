-- ============================================================
-- 多租户数据表
-- ============================================================

-- 租户表
CREATE TABLE IF NOT EXISTS tenants (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(64) NOT NULL UNIQUE,      -- 租户标识
    name            VARCHAR(128) NOT NULL,            -- 租户名称
    type            VARCHAR(32) DEFAULT 'personal',   -- personal/team/enterprise
    status          VARCHAR(32) DEFAULT 'active',     -- active/suspended/deleted
    config          JSONB,                            -- 租户配置
    max_users       INTEGER DEFAULT 10,               -- 最大用户数
    max_storage_mb  INTEGER DEFAULT 1000,             -- 最大存储 MB
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tenants_code ON tenants(code);
CREATE INDEX IF NOT EXISTS ix_tenants_status ON tenants(status);

-- 用户组表
CREATE TABLE IF NOT EXISTS user_groups (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code            VARCHAR(64) NOT NULL,             -- 组标识（租户内唯一）
    name            VARCHAR(128) NOT NULL,            -- 组名称
    description     TEXT,                             -- 描述
    is_default      BOOLEAN DEFAULT FALSE,            -- 是否默认组
    config          JSONB,                            -- 组配置
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
    username        VARCHAR(64) NOT NULL,             -- 用户名（租户内唯一）
    email           VARCHAR(128),                     -- 邮箱
    display_name    VARCHAR(128),                     -- 显示名称
    password_hash   VARCHAR(256),                     -- 密码哈希
    external_id     VARCHAR(128),                     -- 外部系统 ID
    role            VARCHAR(32) DEFAULT 'member',     -- admin/member/viewer
    status          VARCHAR(32) DEFAULT 'active',     -- active/inactive/suspended
    config          JSONB,                            -- 用户配置
    last_login_at   TIMESTAMPTZ,                      -- 最后登录时间
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
    name            VARCHAR(128) NOT NULL,            -- 密钥名称
    key_prefix      VARCHAR(16) NOT NULL,             -- 密钥前缀（如 sk-xxx）
    key_hash        VARCHAR(256) NOT NULL UNIQUE,     -- 密钥哈希
    scopes          JSONB,                            -- 权限范围
    status          VARCHAR(32) DEFAULT 'active',     -- active/revoked
    expires_at      TIMESTAMPTZ,                      -- 过期时间
    last_used_at    TIMESTAMPTZ,                      -- 最后使用时间
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS ix_api_keys_user ON api_keys(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS ix_api_keys_hash ON api_keys(key_hash);

-- ============================================================
-- 为现有表添加 tenant_id（数据迁移用）
-- ============================================================

-- 为 memories 表添加 tenant_id
ALTER TABLE memories ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_memories_tenant ON memories(tenant_id);

-- 为 profiles 表添加 tenant_id
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_profiles_tenant ON profiles(tenant_id);

-- 为 conversation_sessions 表添加 tenant_id
ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_sessions_tenant ON conversation_sessions(tenant_id);

-- 为 memory_generation_jobs 表添加 tenant_id
ALTER TABLE memory_generation_jobs ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_jobs_tenant ON memory_generation_jobs(tenant_id);

-- ============================================================
-- 初始化默认租户（可选）
-- ============================================================

INSERT INTO tenants (code, name, type, status, max_users, max_storage_mb)
VALUES ('default', '默认租户', 'personal', 'active', 100, 10000)
ON CONFLICT (code) DO NOTHING;

-- 为默认租户创建默认用户组
INSERT INTO user_groups (tenant_id, code, name, is_default)
SELECT id, 'default', '默认组', TRUE
FROM tenants WHERE code = 'default'
ON CONFLICT (tenant_id, code) DO NOTHING;
