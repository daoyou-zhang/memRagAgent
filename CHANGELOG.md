# Changelog

## [2024-12-14] - Prompt 自进化架构重构

### 🎯 设计原则
融合三种哲学思想：
- **道家**：有生于无 —— 从原则生成领域能力
- **康德**：道德律令 —— PROMPT_PRINCIPLES 作为普遍准则
- **杜威**：实用主义 —— 以用户需求为导向，系统在使用中成长

### ✨ 新增
- `PROMPT_PRINCIPLES`: 核心原则定义（身份/合规/向善/专业/交互）
- `build_domain_prompt()`: 领域 Prompt 生成器
- `GET /api/v1/prompts/principles`: 获取生成原则 API
- `POST /api/v1/prompts/generate`: 根据原则生成领域 Prompt
- MCP 协议执行器 `_execute_mcp()` 实现
- Prompt 自进化应用到数据库 `apply_evolution()`

### 🔄 重构
- `prompts.py`: 移除行业特定 Prompt，只保留原则
- `cognitive_controller.py`: 实现数据库 Prompt 优先级
  - 请求参数 > 数据库 project > 数据库 category > 代码原则
- `api/prompts.py`: 移除代码预设依赖，改用数据库查询

### 🗑️ 移除
- `INDUSTRY_PROMPTS` 字典
- `PROJECT_PROMPTS` 字典
- `get_prompt_for_industry()` 函数
- `get_prompt_for_project()` 函数
- `get_prompt_for_context()` 函数

### 📁 Prompt 优先级
```
1. 请求参数（最高）
2. 数据库 project 配置
3. 数据库 category 配置
4. 代码原则（最低）
```

---

## [2024-12-13] - 后端 API 测试套件

### ✨ 新增
- `tests/test_memory_api.py`: Memory 服务测试
- `tests/test_knowledge_api.py`: Knowledge 服务测试
- `tests/test_agent_api.py`: Agent 服务测试
- `tests/test_integration.py`: 集成测试
- `tests/TESTING_GUIDE.md`: 测试指南
- `pytest.ini`: pytest 配置
- Tools API CRUD 数据库持久化

### 🔧 修复
- 测试超时处理
- HTTP 方法和路径修正
- 字段名称映射（content → text）
