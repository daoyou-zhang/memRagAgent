-- 完整的数据库重建脚本 - 包含删除和重建所有表

-- ========== 第一步：删除所有相关对象 ==========

-- 1. 删除触发器
DROP TRIGGER IF EXISTS refresh_stats_after_insert ON chat_message;
DROP TRIGGER IF EXISTS refresh_stats_after_session_update ON chat_session;
DROP TRIGGER IF EXISTS update_session_updated_at ON chat_session;
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_service_types_updated_at ON service_types;
DROP TRIGGER IF EXISTS update_user_service_levels_updated_at ON user_service_levels;
DROP TRIGGER IF EXISTS update_ai_prompts_updated_at ON ai_prompts;

-- 2. 删除函数
DROP FUNCTION IF EXISTS refresh_chat_session_stats();
DROP FUNCTION IF EXISTS update_updated_at_column();

-- 3. 删除物化视图
DROP MATERIALIZED VIEW IF EXISTS chat_session_stats;

-- 4. 删除表（注意顺序：先删有外键的表）
DROP TABLE IF EXISTS chat_message;
DROP TABLE IF EXISTS chat_session;
DROP TABLE IF EXISTS user_service_levels;
DROP TABLE IF EXISTS ai_prompts;
DROP TABLE IF EXISTS service_types;
DROP TABLE IF EXISTS reward_settlement;
DROP TABLE IF EXISTS rewards;
DROP TABLE IF EXISTS wechat_accounts;
DROP TABLE IF EXISTS users;

-- 5. 删除序列（在表删除后）
DROP SEQUENCE IF EXISTS chat_message_order_seq;

-- ========== 第二步：重建所有表 ==========

-- 用户表（users）PostgreSQL 建表语句
CREATE TABLE users (
    -- 自增主键，改为 UUID 类型
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    -- 手机号，唯一约束 + 格式校验（正则匹配中国大陆手机号）
    phone VARCHAR(11) UNIQUE CHECK (phone ~ '^1[3-9]\d{9}$'),
    -- 密码哈希值，建议存 bcrypt 等强哈希结果
    password_hash VARCHAR(60) NOT NULL,
    -- 微信开放平台 ID，做唯一约束
    openid VARCHAR(100) UNIQUE,
    unionid VARCHAR(100) UNIQUE,
    -- 微信昵称、头像
    wechat_nickname VARCHAR(100),
    wechat_avatar TEXT,  -- 改为 TEXT 类型
    -- 推荐人关联，外键指向本表 id，类型改为 UUID
    referrer_id UUID REFERENCES users(id),
    -- 是否为推荐人标记
    is_referrer BOOLEAN DEFAULT FALSE,
    -- 记录创建时间（默认当前时间）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 记录更新时间（后续可结合触发器自动更新）
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 最后登录时间
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 为高频查询字段建索引，加速查询
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_openid ON users(openid);
CREATE INDEX idx_users_unionid ON users(unionid);
CREATE INDEX idx_users_phone_lower ON users(lower(phone));  -- 处理手机号大小写问题

-- 聊天会话表
CREATE TABLE chat_session (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),  -- 改为 UUID 类型
    service_type VARCHAR(32) NOT NULL,  -- 改为枚举类型
    main_type VARCHAR(32) NOT NULL,  -- 改为枚举类型
    session_name VARCHAR(128),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    message_count INTEGER DEFAULT 0  -- 新增：会话消息数量，用于后台批量处理判断
);

-- 聊天会话表索引
CREATE INDEX idx_chat_session_user ON chat_session(user_id);
CREATE INDEX idx_chat_session_type ON chat_session(service_type, main_type);
CREATE INDEX idx_chat_session_deleted ON chat_session(is_deleted) WHERE is_deleted = FALSE;  -- 软删除索引

-- 聊天消息表
CREATE SEQUENCE chat_message_order_seq;  -- 专用序列

CREATE TABLE chat_message (
    id bigserial PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_session(session_id),
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_rag TEXT,  -- 改为 TEXT 类型
    order_num BIGINT DEFAULT nextval('chat_message_order_seq'),  -- 使用专用序列
    message_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE (session_id, order_num)
);

-- 聊天消息表索引
CREATE INDEX idx_chat_message_session ON chat_message(session_id);
CREATE INDEX idx_chat_message_order ON chat_message(session_id, order_num);
CREATE INDEX idx_chat_message_session_time ON chat_message(session_id, message_time DESC);  -- 复合索引

-- 服务类型表
CREATE TABLE service_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(32) NOT NULL UNIQUE,  -- 如 jia_wood
    title VARCHAR(64) NOT NULL,  -- 如 甲道友
    description TEXT NOT NULL,  -- 角色描述
    icon_name VARCHAR(32),  -- 图标名称
    color VARCHAR(16) NOT NULL,  -- 主题色
    gradient TEXT NOT NULL,  -- 渐变背景
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 为服务类型表添加索引
CREATE INDEX idx_service_types_key ON service_types(key);

-- ========== 新增：用户等级系统表 ==========

-- 用户等级表 - 记录每个用户在各服务类型下的等级
CREATE TABLE user_service_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_key VARCHAR(32) NOT NULL,  -- 对应service_types表的key
    level INTEGER NOT NULL DEFAULT 1,  -- 用户等级，1-10级
    experience_points INTEGER NOT NULL DEFAULT 0,  -- 经验值
    unlock_status BOOLEAN DEFAULT TRUE,  -- 是否解锁该服务
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, service_key)
);

-- 用户等级表索引
CREATE INDEX idx_user_service_levels_user ON user_service_levels(user_id);
CREATE INDEX idx_user_service_levels_service ON user_service_levels(service_key);
CREATE INDEX idx_user_service_levels_user_service ON user_service_levels(user_id, service_key);

-- AI角色Prompt配置表
CREATE TABLE ai_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_key VARCHAR(32) NOT NULL,  -- 对应service_types表的key
    level INTEGER NOT NULL,  -- 适用等级，1-10级
    prompt_type VARCHAR(32) NOT NULL,  -- prompt类型：intent(意图理解) / chat(对话) / analysis(分析)
    system_prompt TEXT NOT NULL,  -- 系统提示词
    user_prompt_template TEXT,  -- 用户提示词模板（可选）
    is_active BOOLEAN DEFAULT TRUE,  -- 是否启用
    priority INTEGER DEFAULT 0,  -- 优先级，数字越大优先级越高
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service_key, level, prompt_type)
);

-- AI角色Prompt表索引
CREATE INDEX idx_ai_prompts_service ON ai_prompts(service_key);
CREATE INDEX idx_ai_prompts_level ON ai_prompts(level);
CREATE INDEX idx_ai_prompts_type ON ai_prompts(prompt_type);
CREATE INDEX idx_ai_prompts_active ON ai_prompts(is_active) WHERE is_active = TRUE;

-- ========== 触发器函数 ==========

-- 更新时间戳触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 用户表触发器
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 会话表触发器
CREATE TRIGGER update_session_updated_at
BEFORE UPDATE ON chat_session
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 服务类型表触发器
CREATE TRIGGER update_service_types_updated_at
BEFORE UPDATE ON service_types
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 用户等级表触发器
CREATE TRIGGER update_user_service_levels_updated_at
BEFORE UPDATE ON user_service_levels
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- AI角色Prompt表触发器
CREATE TRIGGER update_ai_prompts_updated_at
BEFORE UPDATE ON ai_prompts
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();


-- ========== 注释 ==========

-- 添加表和字段注释
COMMENT ON TABLE users IS '用户基础信息表';
COMMENT ON COLUMN users.id IS '用户唯一标识，UUID 类型';
COMMENT ON COLUMN users.phone IS '手机号，唯一且需符合中国大陆手机号格式';
COMMENT ON COLUMN users.referrer_id IS '推荐人ID，关联本表，形成用户推荐关系';

COMMENT ON TABLE chat_session IS '聊天会话表，记录用户的聊天会话信息';
COMMENT ON COLUMN chat_session.is_deleted IS '软删除标记，TRUE 表示已删除';

COMMENT ON TABLE chat_message IS '聊天消息详情表，记录会话中的具体消息';
COMMENT ON COLUMN chat_message.content_rag IS '检索增强生成内容（RAG），存储相关上下文信息';

COMMENT ON TABLE service_types IS 'AI陪伴角色类型配置表';
COMMENT ON COLUMN service_types.key IS '角色唯一标识，如 jia_wood';
COMMENT ON COLUMN service_types.title IS '角色显示名称，如 甲道友';
COMMENT ON COLUMN service_types.description IS '角色详细描述';
COMMENT ON COLUMN service_types.icon_name IS '角色图标名称';
COMMENT ON COLUMN service_types.color IS '角色主题色';
COMMENT ON COLUMN service_types.gradient IS '角色渐变背景';

COMMENT ON TABLE user_service_levels IS '用户服务等级表，记录用户在各AI角色下的等级和经验';
COMMENT ON COLUMN user_service_levels.service_key IS '服务类型标识，对应service_types表的key字段';
COMMENT ON COLUMN user_service_levels.level IS '用户等级，1-10级，影响AI角色的专业程度';
COMMENT ON COLUMN user_service_levels.experience_points IS '经验值，用于等级升级计算';
COMMENT ON COLUMN user_service_levels.unlock_status IS '解锁状态，控制用户是否可以使用该AI角色';

COMMENT ON TABLE ai_prompts IS 'AI角色Prompt配置表，存储不同等级下的对话提示词';
COMMENT ON COLUMN ai_prompts.service_key IS '服务类型标识，对应service_types表的key字段';
COMMENT ON COLUMN ai_prompts.level IS '适用等级，1-10级，不同等级对应不同专业程度的Prompt';
COMMENT ON COLUMN ai_prompts.prompt_type IS 'Prompt类型：intent(意图理解) / chat(对话) / analysis(分析)';
COMMENT ON COLUMN ai_prompts.system_prompt IS '系统提示词，定义AI角色的身份和行为';
COMMENT ON COLUMN ai_prompts.user_prompt_template IS '用户提示词模板，用于特殊场景的提示词格式化';
COMMENT ON COLUMN ai_prompts.priority IS '优先级，当同一服务类型和等级有多个Prompt时，选择优先级最高的'; 