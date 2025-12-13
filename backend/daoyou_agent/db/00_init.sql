-- ============================================================
-- 道友认知服务 - 数据库初始化脚本
-- 数据库：daoyou（与 knowledge 共用）
-- 
-- 执行方式：
-- psql -h 118.178.183.54 -U daoyou_user -d daoyou -f 00_init.sql
-- 
-- 或分步执行：
-- psql -f 01_mcp_tools.sql
-- psql -f 02_prompt_configs.sql
-- psql -f 03_seed_data.sql
-- ============================================================

\echo '=============================='
\echo '开始初始化道友认知服务数据库'
\echo '=============================='

-- 1. MCP 工具表
\echo '创建 mcp_tools 表...'
\i 01_mcp_tools.sql

-- 2. Prompt 配置表
\echo '创建 prompt_configs 表...'
\i 02_prompt_configs.sql

-- 3. 种子数据
\echo '插入种子数据...'
\i 03_seed_data.sql

\echo '=============================='
\echo '数据库初始化完成！'
\echo '=============================='

-- 验证
\echo '表列表：'
\dt mcp_tools
\dt prompt_configs

\echo 'MCP 工具数量：'
SELECT COUNT(*) FROM mcp_tools;

\echo 'Prompt 配置数量：'
SELECT COUNT(*) FROM prompt_configs;
