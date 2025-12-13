-- ============================================================
-- Prompt 进化历史表
-- 记录每次 prompt 优化的变更历史
-- 数据库：memory
-- ============================================================

CREATE TABLE IF NOT EXISTS prompt_evolution_history (
    id SERIAL PRIMARY KEY,
    
    -- 关联信息
    user_id VARCHAR(64),                -- 用户级优化
    project_id VARCHAR(128),            -- 项目级优化
    category VARCHAR(32),               -- 意图分类（divination/legal/medical...）
    
    -- 触发信息
    trigger_type VARCHAR(32) NOT NULL,  -- 触发类型：profile_aggregate/reflection_low_score/manual
    trigger_reason TEXT,                -- 触发原因详情
    trigger_job_id INT,                 -- 关联的 Job ID（如有）
    
    -- 变更内容
    prompt_type VARCHAR(32) NOT NULL,   -- prompt 类型：intent_system/response_system/response_user
    before_prompt TEXT,                 -- 优化前的 prompt
    after_prompt TEXT,                  -- 优化后的 prompt
    suggestion TEXT,                    -- LLM 给出的优化建议
    
    -- 效果评估
    status VARCHAR(32) DEFAULT 'pending',  -- pending/applied/rejected/reverted
    applied_at TIMESTAMP,               -- 应用时间
    evaluation_score FLOAT,             -- 效果评分（基于后续对话）
    evaluation_count INT DEFAULT 0,     -- 评估样本数
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_prompt_evo_user ON prompt_evolution_history(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_evo_project ON prompt_evolution_history(project_id);
CREATE INDEX IF NOT EXISTS idx_prompt_evo_category ON prompt_evolution_history(category);
CREATE INDEX IF NOT EXISTS idx_prompt_evo_status ON prompt_evolution_history(status);
CREATE INDEX IF NOT EXISTS idx_prompt_evo_trigger ON prompt_evolution_history(trigger_type);

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_prompt_evolution_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_prompt_evolution_updated_at ON prompt_evolution_history;
CREATE TRIGGER trigger_prompt_evolution_updated_at
    BEFORE UPDATE ON prompt_evolution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_prompt_evolution_updated_at();

-- 注释
COMMENT ON TABLE prompt_evolution_history IS 'Prompt 自进化历史记录';
COMMENT ON COLUMN prompt_evolution_history.trigger_type IS '触发类型：profile_aggregate-画像聚合时触发，reflection_low_score-低分反馈触发，manual-手动触发';
COMMENT ON COLUMN prompt_evolution_history.status IS '状态：pending-待应用，applied-已应用，rejected-已拒绝，reverted-已回滚';
