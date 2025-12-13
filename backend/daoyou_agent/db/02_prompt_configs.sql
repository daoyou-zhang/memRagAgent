-- ============================================================
-- Prompt 配置表
-- 支持按行业（category）和项目（project_id）配置不同的 Prompt
-- 数据库：daoyou（与 knowledge 共用）
-- ============================================================

-- Prompt 配置表
CREATE TABLE IF NOT EXISTS prompt_configs (
    id SERIAL PRIMARY KEY,
    
    -- 主键：category 或 project_id（至少有一个）
    category VARCHAR(32),              -- 意图分类：divination/legal/medical/testing 等
    project_id VARCHAR(64),            -- 项目 ID（优先级高于 category）
    
    -- 配置名称
    name VARCHAR(128) NOT NULL,        -- 配置名称（如"八字命理"）
    description TEXT,                  -- 描述
    
    -- Prompt 内容（为空则使用代码默认值）
    intent_system_prompt TEXT,         -- 意图分析 system prompt
    intent_user_template TEXT,         -- 意图分析 user template
    response_system_prompt TEXT,       -- 回复生成 system prompt
    response_user_template TEXT,       -- 回复生成 user template
    
    -- 状态
    enabled BOOLEAN DEFAULT true,
    priority INT DEFAULT 0,            -- 同一 category 多个配置时的优先级
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 约束：category 和 project_id 至少有一个
    CONSTRAINT chk_prompt_key CHECK (category IS NOT NULL OR project_id IS NOT NULL)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_prompt_configs_category ON prompt_configs(category);
CREATE INDEX IF NOT EXISTS idx_prompt_configs_project ON prompt_configs(project_id);
CREATE INDEX IF NOT EXISTS idx_prompt_configs_enabled ON prompt_configs(enabled);

-- 唯一约束：同一 category 或 project_id 只能有一个启用的配置
CREATE UNIQUE INDEX IF NOT EXISTS idx_prompt_configs_category_unique 
    ON prompt_configs(category) WHERE project_id IS NULL AND enabled = true;
CREATE UNIQUE INDEX IF NOT EXISTS idx_prompt_configs_project_unique 
    ON prompt_configs(project_id) WHERE project_id IS NOT NULL AND enabled = true;

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_prompt_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_prompt_configs_updated_at ON prompt_configs;
CREATE TRIGGER trigger_prompt_configs_updated_at
    BEFORE UPDATE ON prompt_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_prompt_configs_updated_at();
