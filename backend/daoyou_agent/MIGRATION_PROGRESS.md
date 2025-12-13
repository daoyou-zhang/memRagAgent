# DaoyouAgent 迁移进度文档

> 将原 `daoyouAgent` 的认知能力迁移到 `memRagAgent` 项目中，作为上层认知服务调用底层记忆/知识服务。

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (React + Vite)                      │
│                    localhost:5173                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  认知测试台     │  │  记忆控制台  │  │  知识库管理   │  │
│  │  /cognitive     │  │  /memories   │  │  /knowledge   │  │
│  └────────┬────────┘  └──────┬───────┘  └───────┬───────┘  │
│           │                  │                   │          │
└───────────┼──────────────────┼───────────────────┼──────────┘
            │                  │                   │
            ▼                  ▼                   ▼
┌───────────────────┐  ┌──────────────┐  ┌───────────────────┐
│  daoyou_agent     │  │   memory     │  │    knowledge      │
│  FastAPI :8000    │──│  Flask :5000 │  │   Flask :?        │
│  认知/意图/MCP    │  │  记忆/RAG    │  │   知识库/图谱     │
└───────────────────┘  └──────────────┘  └───────────────────┘
            │                  │
            │   HTTP 调用      │
            └──────────────────┘
```

---

## 已完成 ✅

### 1. 项目结构搭建
- [x] 创建 `backend/daoyou_agent/` 目录结构
- [x] FastAPI 应用入口 `app.py`
- [x] 包初始化文件 `__init__.py`
- [x] 环境配置 `.env`

### 2. 核心模块迁移
| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 数据模型 | `models/cognitive.py` | ✅ 完成 | CognitiveRequest/Response, Intent, MemoryType 等 |
| 认知控制器 | `services/cognitive_controller.py` | ✅ 完成 | 意图理解→上下文聚合→回复生成→学习闭环 |
| 上下文聚合器 | `services/context_aggregator.py` | ✅ 完成 | 通过 HTTP 调用 memRag 的 /context/full |
| 记忆客户端 | `services/memory_client.py` | ✅ 完成 | 调用 memRag API：context/full, memories, jobs |
| AI 服务适配器 | `services/ai_service_adapter.py` | ✅ 完成 | 客户端池、意图/回复模型分离、中文注释 |
| Prompt 配置 | `config/prompts.py` | ✅ 完成 | 可配置 Prompt（请求级 > 环境变量 > 默认值） |

### 3. API 端点
| 端点 | 方法 | 状态 | 说明 |
|------|------|------|------|
| `/api/v1/cognitive/process` | POST | ✅ 可用 | 主认知处理接口 |

### 4. 前端测试页面
- [x] `frontend/src/api/cognitive.ts` - API 封装
- [x] `frontend/src/pages/CognitivePage.tsx` - 认知测试台
- [x] 首页入口卡片

### 5. 学习闭环
- [x] 对话后自动写入 episodic 记忆到 memRag
- [x] 触发 profile 自动聚合 Job

---

## 待完成 🚧

### 高优先级

#### 1. ✅ 意图理解增强（已完成）
```
文件: services/cognitive_controller.py
实现: 使用 LLM 分析用户意图，返回 category/confidence/entities/summary/needs_tool
模型: 独立的意图模型（qwen-flash），低温度保证稳定 JSON 输出
```

#### 2. ✅ 自我学习与自我进化（已完成）
```
设计思路:
- daoyou_agent = 思维链（推理决策）
- memory = 学过的知识（记忆存储）
- knowledge/RAG = 手上的工具（知识检索）

已实现（在 memory 服务中）:
- llm_client.py: 新增 extract_knowledge_insights / generate_self_reflection / generate_profile_with_reflection
- models/memory.py: 新增 KnowledgeInsight / SelfReflection 模型
- routes/knowledge.py: 知识洞察 API（提取/审核/推送）
- routes/profiles.py: 画像聚合时自动提取知识洞察（复用 LLM 调用）
- db/knowledge_insights.sql: 知识洞察 + 自我反省表

自我进化流程:
  对话 → episodic → semantic → profile + knowledge_insights → 推送到 knowledge 服务
```

#### 3. ✅ MCP 工具系统（已完成）
```
已实现:
- models/mcp_tool.py           # 工具数据模型
- services/tool_registry.py    # 工具注册表（预设 + 数据库）
- services/tool_executor.py    # 工具执行器（本地/HTTP/MCP）
- services/tool_orchestrator.py # 工具编排器（LLM 决策 + 执行）
- tools/bazi.py                # 八字排盘工具（从旧版迁移）
- sql/mcp_tools.sql            # 数据库表定义
- cognitive_controller.py      # 已集成工具调用

待完成:
- API 端点暴露（直接调用工具）
- 前端工具管理界面
```

#### 5. WebSocket 流式响应
```
文件: api/cognitive.py
当前: 仅支持同步 HTTP 请求
目标: 支持 WebSocket 流式输出 LLM 回答
```

### 中优先级

#### 4. 完整上下文构建
```
当前: 只取 memRag 的 profile + working_memory + rag_memories
目标: 
- 加入知识库检索结果
- 加入 MCP 工具上下文
- 更精细的 prompt 组装
```

#### 5. RAG 增强
```
当前: 依赖 memRag 的 rag_memories
目标:
- 支持知识库 RAG（调用 knowledge 服务）
- 混合排序（memory RAG + knowledge RAG）
- 相关性过滤阈值
```

#### 6. 性能监控
```
当前: 记录基础处理时间
目标:
- 各阶段耗时细分（意图/上下文/LLM/学习）
- Token 使用统计
- 错误率监控
```

### 低优先级

#### 7. 多模型支持
```
当前: 固定使用 DashScope/Qwen
目标: 支持切换 OpenAI / 智谱 / 本地模型
```

#### 8. 会话管理
```
- 会话创建/恢复
- 多轮对话上下文窗口
- 会话历史导出
```

#### 9. 前端样式统一
```
目标: 将前端 UI 风格与原 daoyouAgent 统一
涉及: 记忆控制台、知识库管理、认知测试台
```

---

## 启动指南

### 依赖安装
```bash
cd d:\workspace\memRagAgent\backend
pip install fastapi uvicorn httpx loguru python-dotenv
```

### 启动服务

**1. Memory 服务 (端口 5000)**
```bash
cd d:\workspace\memRagAgent\backend\memory
python app.py
```

**2. Daoyou Agent (端口 8000)**
```bash
cd d:\workspace\memRagAgent\backend
uvicorn daoyou_agent.app:create_app --factory --reload
```

**3. 前端 (端口 5173)**
```bash
cd d:\workspace\memRagAgent\frontend
npm run dev
```

### 测试认知 API
```bash
curl -X POST http://127.0.0.1:8000/api/v1/cognitive/process \
  -H "Content-Type: application/json" \
  -d '{"input": "你好", "user_id": "test", "session_id": "s1", "project_id": "p1"}'
```

---

## 文件结构

```
backend/daoyou_agent/
├── __init__.py
├── app.py                 # FastAPI 入口
├── .env                   # LLM 配置
├── MIGRATION_PROGRESS.md  # 本文档
├── api/
│   ├── __init__.py
│   └── cognitive.py       # 认知 API 路由
├── config/
│   ├── __init__.py
│   └── prompts.py         # Prompt 配置
├── models/
│   ├── __init__.py
│   ├── cognitive.py       # 认知数据模型
│   └── mcp_tool.py        # MCP 工具数据模型
├── services/
│   ├── __init__.py
│   ├── ai_service_adapter.py    # LLM 适配器
│   ├── cognitive_controller.py  # 认知控制器（集成工具调用）
│   ├── context_aggregator.py    # 上下文聚合
│   ├── memory_client.py         # memRag HTTP 客户端
│   ├── tool_registry.py         # 工具注册表
│   ├── tool_executor.py         # 工具执行器
│   └── tool_orchestrator.py     # 工具编排器（LLM 决策）
├── tools/
│   ├── __init__.py
│   └── bazi.py            # 八字排盘工具
└── db/
    ├── README.md          # 数据库说明
    ├── 00_init.sql        # 一键初始化脚本
    ├── 01_mcp_tools.sql   # MCP 工具表
    ├── 02_prompt_configs.sql  # Prompt 配置表
    └── 03_seed_data.sql   # 种子数据
```

---

## Services 目录详解

### 1. `ai_service_adapter.py` — LLM 适配器

**职责**：调用 LLM（大语言模型）API

| 类/函数 | 说明 |
|--------|------|
| `LLMConfig` | 配置类（api_base, model_name, temperature 等） |
| `LLMClient` | 单个客户端，负责调用 OpenAI 兼容 API |
| `LLMClientPool` | 客户端池，按配置指纹复用（避免重复创建） |
| `get_intent_client()` | 获取意图分析客户端（qwen-flash，低温度 0.1） |
| `get_response_client()` | 获取回复生成客户端（deepseek，温度 0.5） |

### 2. `cognitive_controller.py` — 认知控制器（核心）

**职责**：协调整个认知流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                   CognitiveController                        │
│                                                             │
│  1. _understand_intent()    → 调用 intent_client 分析意图   │
│  2. get_cognitive_context() → 调用 ContextAggregator        │
│  3. _build_response_prompt() → 组装回复 prompt              │
│  4. response_client.generate() → 调用 LLM 生成回复          │
│  5. _learn_from_interaction() → 存记忆 + 触发画像聚合       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
CognitiveResponse（回复内容 + 意图分析 + 处理时间）
```

### 3. `context_aggregator.py` — 上下文聚合器

**职责**：从 memRag 获取上下文信息

| 方法 | 说明 |
|------|------|
| `get_cognitive_context()` | 调用 memRag 的 /api/memory/context/full |

**返回内容**：
- `user_profile`: 用户画像（兴趣、偏好、历史行为总结）
- `working_memory`: 最近对话记录
- `rag_memories`: RAG 检索到的相关记忆

### 4. `memory_client.py` — 记忆客户端

**职责**：与 memRag 服务通信的 HTTP 客户端

| 方法 | 说明 |
|------|------|
| `get_full_context()` | 获取完整上下文（画像+对话+RAG） |
| `create_memory()` | 创建记忆（情节/语义/程序） |
| `create_profile_job_auto()` | 触发用户画像自动聚合 |

**配置**：环境变量 `MEMORY_SERVICE_BASE_URL`，默认 `http://127.0.0.1:5000`

### 调用关系图

```
                    CognitiveController
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ai_service_adapter  context_aggregator  memory_client
    (调用 LLM)          (聚合上下文)        (读写记忆)
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ DashScope│    │  memRag  │    │  memRag  │
    │ /DeepSeek│    │ :5000    │    │ :5000    │
    └──────────┘    └──────────┘    └──────────┘
```

---

## 配置说明

### daoyou_agent/.env
```env
# 主模型（回复生成）
MODEL_NAME=deepseek-v3.2-exp
MODEL_PROVIDER=qwen
API_MODEL_KEYS=sk-xxx,sk-yyy
API_MODEL_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_MAX_TOKENS=6000
MODEL_TEMPERATURE=0.5

# 意图模型（可选，不配则用主模型）
INTENT_MODEL_NAME=qwen-flash
INTENT_API_KEYS=sk-xxx
INTENT_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
INTENT_MAX_TOKENS=2000
INTENT_TEMPERATURE=0.1

# Prompt 配置（可选）
# PROMPT_INTENT_SYSTEM=你是意图分析专家...
# PROMPT_RESPONSE_SYSTEM=你是道友，智能认知助手...
```

### 依赖的外部服务
| 服务 | 地址 | 用途 |
|------|------|------|
| memRag Memory | http://127.0.0.1:5000 | 记忆存储/检索/RAG |
| DashScope LLM | https://dashscope.aliyuncs.com | 大模型推理 |
| PostgreSQL | 118.178.183.54:5432 | 数据库（通过 memRag） |

---

## MCP 工具系统详解

### 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      工具配置层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 系统预设工具  │  │ 项目定制工具  │  │ 用户专属工具  │      │
│  │ (代码定义)   │  │ (数据库)     │  │ (数据库)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ToolRegistry 工具注册表                     │
│  - 预设工具（代码定义，始终可用）                            │
│  - 数据库工具（动态加载，按 scope 过滤）                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ToolExecutor 工具执行器                     │
│  - local: 本地 Python 函数                                  │
│  - http: HTTP API 调用                                      │
│  - mcp: MCP 协议（待实现）                                  │
└─────────────────────────────────────────────────────────────┘
```

### 工具作用域（Scope）

| 类型 | 说明 | 存储位置 |
|------|------|----------|
| `system` | 系统级，所有用户可用 | 代码预设 / 数据库 |
| `project` | 项目级，指定项目可用 | 数据库 |
| `user` | 用户级，指定用户可用 | 数据库 |

### 已实现的工具

| 工具名 | 类型 | 说明 |
|--------|------|------|
| `bazi_paipan` | local | 八字排盘，计算四柱/大运/五行 |

### 预留的工具（待实现）

| 工具名 | 类型 | 说明 |
|--------|------|------|
| `web_search` | http | 网页搜索 |
| `knowledge_search` | http | 知识库检索 |
| `datetime_info` | local | 日期时间工具 |

### 数据库表

位置: `sql/mcp_tools.sql`，使用与 knowledge 相同的数据库（daoyou）。

---

## 后续优化方向

### 1. 工具编排器（Tool Orchestrator）
```
目标: 根据意图分析结果，自动选择合适的工具
实现思路:
- 意图分析返回 needs_tool=true 时，列出可用工具
- 让 LLM 决定使用哪个工具、填什么参数
- 执行工具，将结果融入最终回复
```

### 2. 自反省能力（Self-Reflection）
```
目标: 分析对话质量，识别改进点
实现思路:
- 对话结束后，用 LLM 评估回复质量
- 记录评估结果到 episodic 记忆
- 定期聚合反思，提炼改进策略
```

### 3. 程序记忆利用（Procedural Memory）
```
目标: 记住"如何做某事"的步骤
实现思路:
- 成功的工具调用序列存入 procedural 记忆
- 下次遇到类似问题，直接复用
- 支持用户自定义流程模板
```

### 4. 多模型协作
```
目标: 不同任务用不同模型
已实现:
- intent_client: 意图分析（快速模型）
- response_client: 回复生成（高质量模型）
待扩展:
- tool_client: 工具决策模型
- reflection_client: 反省模型
```

### 5. 流式输出
```
目标: 支持 WebSocket 流式输出
实现思路:
- LLM 支持 stream=true
- WebSocket 端点推送 chunk
- 前端实时渲染
```

---

## 更新日志

### 2025-12-13（深夜）
- ✅ 用户自定义模型配置
  - CognitiveRequest 新增 `model_config_override` 字段
  - 支持 OpenAI、通义千问、DeepSeek、智谱等 OpenAI 兼容 API
  - 回退机制：用户配置 → 环境变量默认配置
- ✅ 文件读取工具
  - tools/file_reader.py（read_file、list_directory）
  - 安全限制：文件类型白名单、大小限制
  - 注册到 MCP 工具系统
- ✅ Redis 缓存优化
  - RAG 查询缓存 5 分钟
  - 图谱搜索缓存 10 分钟
  - 用户画像缓存 10 分钟
- ✅ 统一日志（loguru 替代 print）
- ✅ 前端新增页面
  - 多租户管理 `/tenants`
  - 系统状态 `/system`（服务监控 + 功能测试）
- ✅ 文档更新
  - README.md 完善 API 列表
  - KNOWLEDGE_BASE_DESIGN.md 更新实现状态

### 2024-12-13（晚上）
- ✅ MCP 工具系统框架
  - models/mcp_tool.py（工具数据模型）
  - services/tool_registry.py（工具注册表）
  - services/tool_executor.py（工具执行器）
  - tools/bazi.py（八字排盘工具迁移）
  - sql/mcp_tools.sql（数据库表）
- ✅ 记录后续优化方向

### 2024-12-13（下午）
- ✅ 实现 LLM 意图理解（用 qwen-flash 分析 category/entities/confidence）
- ✅ 意图/回复模型分离（LLMClientPool 客户端池）
- ✅ 可配置 Prompt 系统（请求级 > 环境变量 > 默认值）
- ✅ 全部代码注释改为中文
- ✅ 更新 MIGRATION_PROGRESS.md 文档

### 2024-12-13（上午）
- 初始化 daoyou_agent FastAPI 项目结构
- 迁移认知数据模型
- 实现 MemoryClient 调用 memRag API
- 实现简化版 CognitiveController
- 接入真实 LLM (DashScope/Qwen)
- 创建前端认知测试台
- 实现学习闭环（episodic 写入 + profile Job 触发）
- 修复数据库连接池问题 (pool_pre_ping)

---

## 下一步建议

### 已完成 ✅
1. ~~**工具编排器** — 让意图分析触发工具调用~~ ✅
2. ~~**认知控制器集成** — 工具结果融入回复生成~~ ✅
3. ~~**用户自定义模型** — 支持请求级别配置~~ ✅
4. ~~**文件读取工具** — 代码审查场景~~ ✅

### 待完成 🚧
1. **前端工具管理** — 管理工具的启用/禁用
2. **代码执行沙箱** — 安全运行用户代码
3. **单元测试** — 核心功能测试覆盖
4. **Docker 部署** — 一键启动脚本
