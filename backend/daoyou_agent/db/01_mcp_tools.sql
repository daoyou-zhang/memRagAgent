-- ============================================================
-- MCP 工具系统数据库表
-- 数据库：daoyou（与 knowledge 共用）
-- ============================================================

-- 工具定义表
CREATE TABLE IF NOT EXISTS mcp_tools (
    id SERIAL PRIMARY KEY,
    
    -- 基本信息
    name VARCHAR(64) NOT NULL UNIQUE,      -- 工具唯一标识，如 "bazi_paipan"
    display_name VARCHAR(128) NOT NULL,    -- 显示名称，如 "八字排盘"
    description TEXT NOT NULL,             -- 描述（给 LLM 看，决定是否使用）
    category VARCHAR(32) DEFAULT 'general', -- 分类：general/divination/search/utility/testing
    
    -- 参数定义（JSON Schema 格式）
    parameters JSONB,                      -- 工具参数定义
    
    -- 权限控制
    scope VARCHAR(16) DEFAULT 'system',    -- system: 全局 / project: 项目级 / user: 用户级
    project_ids TEXT[] DEFAULT '{}',       -- scope=project 时，可用的项目 ID 列表
    user_ids TEXT[] DEFAULT '{}',          -- scope=user 时，可用的用户 ID 列表
    
    -- 执行配置
    handler_type VARCHAR(16) DEFAULT 'local', -- local: 本地函数 / http: HTTP API / mcp: MCP 协议
    handler_config JSONB DEFAULT '{}',     -- 执行配置（函数路径/URL/MCP 地址等）
    
    -- 状态
    enabled BOOLEAN DEFAULT true,          -- 是否启用
    priority INT DEFAULT 0,                -- 优先级（同类工具排序）
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_mcp_tools_name ON mcp_tools(name);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_scope ON mcp_tools(scope);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_category ON mcp_tools(category);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_enabled ON mcp_tools(enabled);

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_mcp_tools_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_mcp_tools_updated_at ON mcp_tools;
CREATE TRIGGER trigger_mcp_tools_updated_at
    BEFORE UPDATE ON mcp_tools
    FOR EACH ROW
    EXECUTE FUNCTION update_mcp_tools_updated_at();
