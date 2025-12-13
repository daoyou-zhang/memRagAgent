# 道友认知服务 - 数据库

## 数据库信息

- **数据库**：daoyou（与 knowledge 服务共用）
- **主机**：118.178.183.54
- **端口**：5432
- **用户**：daoyou_user

## 表结构

| 表名 | 说明 | 文件 |
|------|------|------|
| `mcp_tools` | MCP 工具定义 | 01_mcp_tools.sql |
| `prompt_configs` | Prompt 配置（按行业/项目） | 02_prompt_configs.sql |

## 执行顺序

```bash
# 方式1：一键初始化（推荐）
psql -h 118.178.183.54 -U daoyou_user -d daoyou -f 00_init.sql

# 方式2：分步执行
psql -h 118.178.183.54 -U daoyou_user -d daoyou -f 01_mcp_tools.sql
psql -h 118.178.183.54 -U daoyou_user -d daoyou -f 02_prompt_configs.sql
psql -h 118.178.183.54 -U daoyou_user -d daoyou -f 03_seed_data.sql
```

## 表说明

### mcp_tools - MCP 工具表

存储工具定义，支持：
- 系统级工具（所有用户可用）
- 项目级工具（指定项目可用）
- 用户级工具（指定用户可用）

```sql
-- 查看所有工具
SELECT name, display_name, category, enabled FROM mcp_tools;

-- 启用/禁用工具
UPDATE mcp_tools SET enabled = true WHERE name = 'bazi_paipan';
```

### prompt_configs - Prompt 配置表

存储行业/项目 Prompt，查询优先级：
1. `project_id` 精确匹配（最高）
2. `category` 匹配
3. 代码默认值（兜底）

```sql
-- 查看所有配置
SELECT category, project_id, name, enabled FROM prompt_configs;

-- 添加新行业配置
INSERT INTO prompt_configs (category, name, response_system_prompt)
VALUES ('new_category', '新行业', '你是...专业顾问');

-- 添加项目专属配置（优先级高于 category）
INSERT INTO prompt_configs (project_id, name, response_system_prompt)
VALUES ('my_project', '我的项目', '你是...项目专属助手');
```

## 支持的行业（category）

| category | 说明 | 工具 |
|----------|------|------|
| `divination` | 命理占卜 | bazi_paipan |
| `legal` | 法律咨询 | knowledge_search |
| `medical` | 医疗健康 | - |
| `testing` | 软件测试 | api_test |
| `search` | 搜索检索 | web_search, knowledge_search |
| `general` | 通用 | - |
