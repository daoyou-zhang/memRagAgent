-- 创建微信账号关联表
-- 用于关联微信账号和主用户，实现多端登录用户统一

CREATE TABLE IF NOT EXISTS wechat_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    openid VARCHAR(64) UNIQUE NOT NULL,
    unionid VARCHAR(64),
    wechat_type VARCHAR(20) NOT NULL CHECK (wechat_type IN ('miniprogram', 'mp', 'website')),
    wechat_nickname VARCHAR(100),
    wechat_avatar TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    
    -- 外键约束
    CONSTRAINT fk_wechat_accounts_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- 唯一约束
    CONSTRAINT uk_wechat_accounts_openid UNIQUE (openid)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_wechat_accounts_openid ON wechat_accounts(openid);
CREATE INDEX IF NOT EXISTS idx_wechat_accounts_unionid ON wechat_accounts(unionid);
CREATE INDEX IF NOT EXISTS idx_wechat_accounts_user_id ON wechat_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_wechat_accounts_wechat_type ON wechat_accounts(wechat_type);

-- 添加注释
COMMENT ON TABLE wechat_accounts IS '微信账号关联表，用于关联微信账号和主用户';
COMMENT ON COLUMN wechat_accounts.id IS '主键ID';
COMMENT ON COLUMN wechat_accounts.user_id IS '关联的用户ID';
COMMENT ON COLUMN wechat_accounts.openid IS '微信openid，唯一标识';
COMMENT ON COLUMN wechat_accounts.unionid IS '微信unionid，用于多端统一';
COMMENT ON COLUMN wechat_accounts.wechat_type IS '微信账号类型：miniprogram(小程序)/mp(公众号)/website(网站)';
COMMENT ON COLUMN wechat_accounts.wechat_nickname IS '微信昵称';
COMMENT ON COLUMN wechat_accounts.wechat_avatar IS '微信头像URL';
COMMENT ON COLUMN wechat_accounts.created_at IS '创建时间';
COMMENT ON COLUMN wechat_accounts.updated_at IS '更新时间'; 