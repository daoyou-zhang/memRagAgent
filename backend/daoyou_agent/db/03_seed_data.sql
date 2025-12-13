-- ============================================================
-- 种子数据（初始化数据）
-- 执行顺序：在表结构创建后执行
-- ============================================================

-- ============================================================
-- MCP 工具预设数据
-- ============================================================

-- 八字排盘工具
INSERT INTO mcp_tools (name, display_name, description, category, parameters, handler_type, handler_config, enabled, priority)
VALUES (
    'bazi_paipan',
    '八字排盘',
    '根据出生时间和地点，计算八字命盘，包括四柱（年柱、月柱、日柱、时柱）、大运、流年、十神、五行平衡等信息。适用于命理分析、运势预测等场景。',
    'divination',
    '{
        "type": "object",
        "required": ["year", "month", "day", "hour", "gender", "birth_place"],
        "properties": {
            "year": {"type": "integer", "description": "出生年份（1900-2100）", "minimum": 1900, "maximum": 2100},
            "month": {"type": "integer", "description": "出生月份（1-12）", "minimum": 1, "maximum": 12},
            "day": {"type": "integer", "description": "出生日期（1-31）", "minimum": 1, "maximum": 31},
            "hour": {"type": "string", "description": "出生小时（00-23）", "pattern": "^([01][0-9]|2[0-3])$"},
            "minute": {"type": "string", "description": "出生分钟（00-59）", "default": "00"},
            "gender": {"type": "string", "description": "性别", "enum": ["male", "female"]},
            "birth_place": {"type": "string", "description": "出生地点"},
            "calendarType": {"type": "string", "description": "历法类型", "enum": ["solar", "lunar"], "default": "solar"},
            "isLeapMonth": {"type": "boolean", "description": "是否闰月（仅农历有效）", "default": false}
        }
    }',
    'local',
    '{"module": "daoyou_agent.tools.bazi", "function": "calculate_bazi"}',
    true,
    100
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    parameters = EXCLUDED.parameters,
    handler_config = EXCLUDED.handler_config,
    updated_at = NOW();

-- 预留：网页搜索工具
INSERT INTO mcp_tools (name, display_name, description, category, parameters, handler_type, handler_config, enabled, priority)
VALUES (
    'web_search',
    '网页搜索',
    '搜索互联网上的相关信息，返回搜索结果摘要。适用于需要获取最新信息、查找资料等场景。',
    'search',
    '{"type": "object", "required": ["query"], "properties": {"query": {"type": "string", "description": "搜索关键词"}, "limit": {"type": "integer", "description": "返回结果数量", "default": 5}}}',
    'http',
    '{"url": "", "method": "GET"}',
    false,
    50
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 预留：知识库检索工具
INSERT INTO mcp_tools (name, display_name, description, category, parameters, handler_type, handler_config, enabled, priority)
VALUES (
    'knowledge_search',
    '知识库检索',
    '检索内部知识库中的相关文档和信息。适用于需要查找专业知识、历史记录等场景。',
    'search',
    '{"type": "object", "required": ["query"], "properties": {"query": {"type": "string", "description": "检索内容"}, "top_k": {"type": "integer", "description": "返回结果数量", "default": 5}}}',
    'http',
    '{"url": "http://127.0.0.1:5001/api/knowledge/search", "method": "POST"}',
    false,
    60
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 预留：API 测试工具
INSERT INTO mcp_tools (name, display_name, description, category, parameters, handler_type, handler_config, enabled, priority)
VALUES (
    'api_test',
    'API 测试',
    '测试 HTTP API 接口，支持 GET/POST/PUT/DELETE 等方法，返回状态码、响应时间、响应内容等。',
    'testing',
    '{"type": "object", "required": ["url"], "properties": {"url": {"type": "string", "description": "API 地址"}, "method": {"type": "string", "description": "HTTP 方法", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"}, "headers": {"type": "object", "description": "请求头"}, "body": {"type": "object", "description": "请求体"}}}',
    'local',
    '{"module": "daoyou_agent.tools.testing", "function": "api_test"}',
    false,
    70
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    updated_at = NOW();

-- ============================================================
-- Prompt 配置预设数据
-- ============================================================

-- 八字命理行业
INSERT INTO prompt_configs (category, name, description, response_system_prompt, enabled, priority)
VALUES (
    'divination',
    '八字命理',
    '八字命理、占卜相关的专业回复配置',
    '你是道友，一位精通八字命理的专业顾问。

你的专业能力：
- 精通四柱八字、十神关系、五行生克
- 能够解读大运流年、分析命局格局
- 结合现代语言解释传统命理知识
- 给出有建设性的人生建议

注意事项：
- 基于工具返回的八字数据进行专业解读
- 用通俗易懂的语言解释命理术语
- 避免过于绝对的断言，强调命理仅供参考
- 保持积极正面的引导',
    true,
    100
) ON CONFLICT DO NOTHING;

-- 法律咨询行业
INSERT INTO prompt_configs (category, name, description, response_system_prompt, enabled, priority)
VALUES (
    'legal',
    '法律咨询',
    '法律咨询相关的专业回复配置',
    '你是道友，一位专业的法律顾问助手。

你的专业能力：
- 熟悉中国法律法规体系
- 能够提供法律问题的初步分析
- 引导用户了解相关法律条款
- 建议何时需要寻求专业律师帮助

注意事项：
- 基于检索到的法律知识回答
- 明确说明这是法律咨询参考，非正式法律意见
- 涉及重大法律问题建议寻求专业律师
- 保持客观中立',
    true,
    100
) ON CONFLICT DO NOTHING;

-- 医疗健康行业
INSERT INTO prompt_configs (category, name, description, response_system_prompt, enabled, priority)
VALUES (
    'medical',
    '医疗健康',
    '医疗健康咨询相关的专业回复配置',
    '你是道友，一位健康咨询助手。

你的专业能力：
- 了解常见疾病的基本知识
- 能够提供健康生活建议
- 引导用户了解健康知识

注意事项：
- 明确说明这不是医疗诊断
- 任何疾病症状都建议就医检查
- 不推荐具体药物
- 关注用户心理健康',
    true,
    100
) ON CONFLICT DO NOTHING;

-- 测试行业
INSERT INTO prompt_configs (category, name, description, response_system_prompt, enabled, priority)
VALUES (
    'testing',
    '软件测试',
    '软件测试、API测试、UI测试相关的专业回复配置',
    '你是道友，一位专业的软件测试工程师助手。

你的专业能力：
- 熟悉 UI 自动化测试（Selenium/Playwright/Cypress）
- 精通 API 接口测试（Postman/REST/GraphQL）
- 了解链路测试、性能测试、安全测试
- 能够编写测试用例、分析测试报告

注意事项：
- 基于工具返回的测试结果进行分析
- 提供可执行的测试建议
- 帮助定位问题根因
- 给出改进建议',
    true,
    100
) ON CONFLICT DO NOTHING;
