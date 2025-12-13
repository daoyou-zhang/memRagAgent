# memRagAgent - Memory 服务

记忆管理服务，负责对话记忆存储、语义提取、画像聚合、知识洞察和自我反省。

## 架构定位

```
┌─────────────────────────────────────────────────────────────┐
│                    daoyou_agent (思维链)                     │
│        意图理解 → 工具调用 → 上下文聚合 → 回复生成            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    memory (记忆系统)                         │
│  episodic → semantic → profile → knowledge_insights         │
│              自我学习、自我进化                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   knowledge (知识库)                         │
│              RAG 检索、知识存储                              │
└─────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 记忆层级

| 类型 | 说明 | 生命周期 |
|------|------|----------|
| **episodic** | 情节记忆，对话摘要 | 短期 |
| **semantic** | 语义记忆，用户偏好/事实 | 长期 |
| **profile** | 用户画像，聚合结果 | 持久 |

### 2. 自我学习（新增）

```
对话结束
    │
    ▼
episodic 记忆生成
    │
    ▼
semantic 记忆提取（用户偏好、事实）
    │
    ▼
profile 聚合（同时提取知识洞察）
    │
    ├─→ 知识洞察 → 推送到 knowledge 服务
    │
    └─→ 反省总结 → 改进策略
```

### 3. 知识洞察提取

从对话中提取可复用的知识，丰富知识库：

- **domain**: 领域专业知识
- **skill**: 技能技巧
- **fact**: 事实信息
- **pattern**: 模式规律
- **general**: 通用知识

## API 接口

### Memory API (`/api/memory`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/` | 创建记忆 |
| GET | `/<memory_id>` | 获取记忆 |
| GET | `/search` | 搜索记忆 |
| POST | `/jobs` | 创建记忆生成任务 |
| POST | `/jobs/<id>/run` | 执行任务 |

### Profile API (`/api/profiles`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/<user_id>` | 获取用户画像（自动聚合+知识提取） |

### Knowledge API (`/api/knowledge`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/insights` | 获取知识洞察列表 |
| POST | `/extract` | 手动触发知识提取 |
| POST | `/insights/<id>/approve` | 审核通过 |
| POST | `/insights/<id>/reject` | 拒绝 |
| POST | `/insights/push` | 推送到知识库 |
| GET | `/reflections` | 获取反省记录 |
| GET | `/reflections/stats` | 反省统计 |

### RAG API (`/api/rag`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/query` | RAG 查询 |
| GET | `/context` | 获取上下文 |

## 数据库表

```
memory/db/
├── memories.sql              # 记忆表
├── memory_embeddings.sql     # 向量嵌入
├── memory_generation_jobs.sql # 生成任务
├── conversation_sessions.sql  # 会话
├── conversation_messages.sql  # 消息
├── profiles.sql              # 用户画像
├── profiles_history.sql      # 画像历史
└── knowledge_insights.sql    # 知识洞察 + 自我反省
```

## 环境变量

```bash
# 数据库
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=memrag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Redis 缓存
REDIS_URL=redis://:password@localhost:6379
REDIS_ENABLED=true
REDIS_CACHE_TTL=300

# ChromaDB 向量存储
USE_CHROMADB=true
CHROMA_PERSIST_DIR=./chroma_data

# LLM 配置
API_MODEL_BASE=https://api.example.com/v1
MODEL_NAME=qwen-plus
API_MODEL_KEYS=sk-xxx

# Embedding 配置
EMBEDDINGS_NAME=embedding-3
API_EMBEDDINGS_KEY=xxx
API_EMBEDDINGS_BASE=https://api.example.com/v4

# 功能开关
JOB_SCHEDULER_ENABLED=true
PROFILE_AUTO_REFRESH_ENABLED=true
PROFILE_MIN_NEW_SEMANTIC_FOR_REFRESH=3
UNIFIED_MEMORY_GENERATION=true

# 时间窗口（可选）
JOB_RUN_WINDOW_EPISODIC=
JOB_RUN_WINDOW_SEMANTIC=
JOB_RUN_WINDOW_PROFILE=
```

## 启动服务

```bash
cd backend/memory
python app.py
# 服务运行在 http://localhost:5000
```

## 性能优化

### Redis 缓存
- **Profile 缓存**: 10 分钟 TTL
- **Embedding 缓存**: 1 小时 TTL
- **RAG 结果缓存**: 5 分钟 TTL

### 数据库连接池
- `pool_size=10`
- `max_overflow=20`
- `pool_pre_ping=True`
- `pool_recycle=300`

### ChromaDB 向量检索
- 批量写入支持
- 自动 fallback 到 JSONB

## 多租户支持

新增租户管理 API (`/api/tenants`):

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tenants` | 创建租户 |
| GET | `/tenants` | 列出租户 |
| POST | `/tenants/:id/groups` | 创建用户组 |
| POST | `/tenants/:id/users` | 创建用户 |
| POST | `/tenants/:id/api-keys` | 创建 API Key |
| POST | `/auth/login` | 用户登录 |
| POST | `/auth/verify-key` | 验证 API Key |

## 自我进化流程

1. **对话产生** → 存储 episodic 记忆
2. **语义提取** → 生成 semantic 记忆（用户偏好、事实）
3. **画像聚合** → 更新 profile + 提取知识洞察
4. **知识审核** → 管理员/自动审核知识洞察
5. **知识推送** → 推送到 knowledge 服务丰富知识库
6. **RAG 增强** → 后续对话使用增强的知识库

## 开发路线

- [x] 基础记忆 CRUD
- [x] 语义记忆提取
- [x] 用户画像聚合
- [x] ChromaDB 向量检索
- [x] Redis 缓存优化
- [x] 多租户支持
- [x] 知识洞察提取
- [ ] 单元测试
- [ ] 知识推送到 knowledge 服务
