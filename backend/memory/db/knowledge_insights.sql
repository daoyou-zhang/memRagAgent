-- knowledge_insights.sql
-- 知识洞察表，存储从对话中提取的可复用知识
-- 这些知识可以推送到 knowledge 服务丰富知识库

CREATE TABLE IF NOT EXISTS knowledge_insights (
    id SERIAL PRIMARY KEY,
    
    -- 来源信息
    user_id TEXT NULL,                    -- 提取来源用户（可为空表示通用知识）
    project_id TEXT NULL,                 -- 项目 ID
    source_type TEXT NOT NULL DEFAULT 'conversation',  -- conversation/reflection/manual
    
    -- 知识内容
    content TEXT NOT NULL,                -- 知识点内容
    category TEXT NOT NULL DEFAULT 'general',  -- 分类：general/domain/skill/fact/pattern
    confidence FLOAT NOT NULL DEFAULT 0.7,     -- 置信度 0-1
    
    -- 元数据
    tags JSONB DEFAULT '[]',              -- 标签数组
    metadata JSONB DEFAULT '{}',          -- 额外元数据
    
    -- 状态
    status TEXT NOT NULL DEFAULT 'pending',    -- pending/approved/rejected/pushed
    pushed_to_knowledge BOOLEAN DEFAULT false, -- 是否已推送到知识库
    pushed_at TIMESTAMPTZ NULL,
    
    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_knowledge_insights_project 
    ON knowledge_insights(project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_insights_category 
    ON knowledge_insights(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_insights_status 
    ON knowledge_insights(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_insights_pushed 
    ON knowledge_insights(pushed_to_knowledge);


-- self_reflections.sql (合并到同一文件)
-- 自我反省记录表，存储对话质量评估和改进建议

CREATE TABLE IF NOT EXISTS self_reflections (
    id SERIAL PRIMARY KEY,
    
    -- 关联信息
    user_id TEXT NOT NULL,
    project_id TEXT NULL,
    session_id TEXT NULL,
    
    -- 评估结果
    satisfaction_score INT NOT NULL DEFAULT 5,  -- 1-10
    problem_solved BOOLEAN DEFAULT false,
    completeness TEXT DEFAULT 'partial',        -- complete/partial/incomplete
    
    -- 反思内容
    strengths JSONB DEFAULT '[]',               -- 做得好的点
    weaknesses JSONB DEFAULT '[]',              -- 可改进的点
    suggestions JSONB DEFAULT '[]',             -- 改进建议
    summary TEXT,                               -- 一句话总结
    
    -- 上下文
    intent_category TEXT,
    tool_used TEXT,
    
    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_self_reflections_user 
    ON self_reflections(user_id, project_id);
CREATE INDEX IF NOT EXISTS idx_self_reflections_score 
    ON self_reflections(satisfaction_score);
CREATE INDEX IF NOT EXISTS idx_self_reflections_created 
    ON self_reflections(created_at);
