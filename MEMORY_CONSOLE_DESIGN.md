# memRagAgent 记忆控制台骨架设计与实现说明

> 目标：为智能记忆中心（Memory Service）搭建一个可视化的“记忆控制台”，方便开发调试与后续对接 RAG / 多 Agent 系统。
>
> 本文档记录从 **后端设计 → 前端设计 → 分页方案 → 双页面拆分** 的完整过程，作为项目的架构说明与实现参考。

---

## 0. 环境准备与搭建步骤（从零到可用控制台）

这一节按时间顺序记录“如何从空目录一步步搭建到现在这套记忆控制台”，方便复现或给新人参考。

### 0.1 基础环境

- 操作系统：Windows
- 依赖：
  - Python 3.10+（建议）
  - Node.js 18+（建议）
  - PostgreSQL 14+（建议）

### 0.2 创建项目根目录

```bash
mkdir memRagAgent
cd memRagAgent
```

此目录作为后续后端 `backend/` 与前端 `frontend/` 的统一根目录，并在根目录下存放设计文档（本文件）。

### 0.3 搭建后端 Memory Service

#### 0.3.1 创建后端目录结构

```bash
mkdir -p backend/memory/backend
cd backend
mkdir memory
cd memory
mkdir models repository routes db
```

规范化结构：

- `app.py` 放在 `backend/memory/app.py`
- `models/memory.py` 存放 ORM 模型
- `repository/db_session.py` 管理数据库连接
- `routes/memories.py` 存放 Flask 路由
- `db/memories.sql` 存放建表 SQL

#### 0.3.2 创建 Python 虚拟环境并安装依赖

```powershell
cd backend\memory
python -m venv .venv
.\.venv\Scripts\activate

pip install Flask SQLAlchemy psycopg2-binary python-dotenv
```

（可根据需要后续加上 `alembic` 等迁移工具，这里先用最简方式。）

#### 0.3.3 配置数据库连接与 .env

在 `backend/memory` 下创建 `.env`：

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mem_rag
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

在 `repository/db_session.py` 中：

- 使用 `load_dotenv()` 读取上述环境变量。
- 拼接 Postgres 连接字符串并创建 `engine` 与 `SessionLocal`。
- 提供 `init_db()` 在应用启动时初始化数据库结构。

#### 0.3.4 定义 Memory 模型

在 `models/memory.py` 中：

1. 定义基础 `Base = declarative_base()`。
2. 定义 `Memory`：
   - 包含 `id, user_id, agent_id, project_id, type, source, text, summary, importance, emotion, tags, extra_metadata, created_at, last_access_at, recall_count`。
   - `tags` 和 `extra_metadata` 使用 `JSONB`。
   - `extra_metadata` 的底层列名映射为 `metadata`，避免 SQLAlchemy 保留字段冲突。

#### 0.3.5 初始化 Flask 应用

在 `backend/memory/app.py` 中：

1. 创建 Flask app。
2. 导入并调用 `init_db()` 初始化数据库。
3. 创建一个 `Blueprint`（如 `memory_bp`），并在 `routes/__init__.py` 中注册各个子蓝图（包括 `memories_bp`）。
4. 注册健康检查路由：`GET /health`。

#### 0.3.6 实现创建与查询路由

在 `routes/memories.py` 中：

1. `POST /memories`：
   - 从请求体中解析各字段；
   - 校验 `text` 必填；
   - 使用 `SessionLocal()` 创建会话，写入 `Memory`；
   - 提交后返回 201 JSON（对外字段仍为 `metadata`）。
2. `POST /memories/query`：
   - 支持 `user_id` / `project_id` / `query` / `top_k` / `page` / `page_size`；
   - 支持 `filters.types` / `filters.min_importance` / `filters.tags`；
   - 对 `tags` 使用 `cast(Memory.tags, TEXT).ilike(...)` 做简单包含过滤；
   - 先 `count()` 得到 `total`，再根据 `page` / `page_size` / `top_k` 分页；
   - 返回 `items + page + page_size + total + has_next + has_prev`。

#### 0.3.7 启动后端进行本地验证

在 `backend/memory` 下：

```powershell
.\.venv\Scripts\activate
python app.py
```

简单用 `curl` / `Invoke-RestMethod` 测试：

- `GET http://localhost:5000/api/memory/health`
- `POST http://localhost:5000/api/memory/memories` 创建一条记忆
- `POST http://localhost:5000/api/memory/memories/query` 查询并检查分页字段

至此，后端 Memory Service 的基本骨架跑通。

### 0.4 搭建前端 React 记忆控制台

#### 0.4.1 创建前端项目

在项目根目录：

```bash
cd ..  # 回到 memRagAgent 根目录
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom
```

这样得到一个 `frontend/` 子目录，采用 Vite + React + TypeScript 模板。

#### 0.4.2 清理默认模板并设置全局样式

1. 删除 Vite 默认的计数器示例组件。
2. 在 `index.css` / `App.css` 中：
   - 移除与 Logo 动画相关样式；
   - 设置整体为浅色控制台风格背景；
   - 为 Header、导航、卡片、表格等添加基础样式。

#### 0.4.3 配置 React Router 与入口

1. 在 `main.tsx` 中，用 `BrowserRouter` 包裹 `App`。
2. 在 `App.tsx` 中：
   - 定义基本布局（Header + 主区域）；
   - 使用 `Routes` / `Route` 配置：
     - `/` → 重定向到 `/memories/create`；
     - `/memories/create` / `/memories/query` / `/rag` / `/profiles`。

#### 0.4.4 抽象 HTTP 与 Memory API

1. 创建 `src/api/http.ts`：
   - 封装 `request` 函数，统一加上 `Content-Type: application/json`；
   - 处理非 2xx 时抛出错误；
   - 自动 `response.json()`。
2. 创建 `src/api/memory.ts`：
   - 定义：
     - `HealthResponse` / `CreateMemoryPayload` / `QueryMemoriesPayload` / `QueryMemoriesResponse` / `QueryResultItem`；
   - 封装：
     - `fetchMemoryHealth()` 调用后端 `/api/memory/health`；
     - `createMemory()` 调用 `/api/memory/memories`；
     - `queryMemories()` 调用 `/api/memory/memories/query` 并接受分页参数。

#### 0.4.5 编写页面组件

1. `pages/MemoryCreatePage.tsx`：
   - 顶部展示健康状态（调用 `fetchMemoryHealth`）。
   - 下方为“植入记忆”表单：用户 ID / 项目 ID / 类型 / 文本 / 标签。
   - 提交时调用 `createMemory`，显示成功或错误信息。
2. `pages/MemoryQueryPage.tsx`：
   - 顶部同样展示健康状态。
   - 查询表单：用户 ID / 项目 ID / 查询内容 / 标签筛选。
   - 提交时调用 `queryMemories`，默认 `page=1` `page_size=10` `top_k=0`；
   - 下方用表格显示结果，并在底部显示中文分页信息和上一页 / 下一页按钮。
3. 在 `App.tsx` 中导入这两个页面，并在 Header 导航中添加：
   - “创建记忆”链接到 `/memories/create`；
   - “查询记忆”链接到 `/memories/query`。

#### 0.4.6 启动前端并联调

在 `frontend` 目录下：

```bash
npm run dev
```

浏览器访问（通常）：`http://localhost:5173/`，会自动跳转到 `/memories/create`。

联调流程示例：

1. 在“创建记忆”页：
   - 确认上方健康状态为正常；
   - 填写用户 ID / 项目 ID / 文本 / 标签，点击“写入记忆”；
   - 查看是否提示“记忆已成功写入”。
2. 切换到“查询记忆”页：
   - 输入相同的用户 ID / 项目 ID；
   - 设置标签筛选或查询文本；
   - 点击“查询记忆”，观察表格与分页是否生效。

至此，记忆控制台的完整骨架（后端 Memory Service + 前端双页控制台）即可正常工作。

---

## 1. 整体架构概览

### 1.1 项目结构（与本次相关部分）

- `backend/memory`
  - `app.py`：Flask 应用入口，注册 Blueprint，初始化数据库，提供健康检查。
  - `models/memory.py`：记忆数据模型 `Memory`。
  - `repository/db_session.py`：SQLAlchemy Session & Engine 管理，Postgres 连接。
  - `routes/memories.py`：记忆相关 REST API：
    - `POST /memories` 创建记忆
    - `POST /memories/query` 查询+分页
  - `db/memories.sql`：建表 SQL（用于直接在数据库中初始化 / 对照）。

- `frontend/src`
  - `api/http.ts`：通用 HTTP 封装（统一错误处理、JSON 解析）。
  - `api/memory.ts`：Memory 相关前端 API 封装（健康、创建、查询）。
  - `api/rag.ts`：RAG 相关 API 占位（后续实现）。
  - `api/profiles.ts`：Profile 相关 API 占位（后续实现）。
  - `pages/MemoryCreatePage.tsx`：**创建（植入）记忆页面**。
  - `pages/MemoryQueryPage.tsx`：**查询 + 分页 浏览记忆页面**。
  - `pages/RagPage.tsx`：RAG 页面占位。
  - `pages/ProfilesPage.tsx`：Profiles 页面占位。
  - `App.tsx`：前端路由与整体布局（导航菜单）。
  - `index.css` / `App.css`：全局样式 + 控制台风格样式。

整体思路：

- 后端：Flask + SQLAlchemy + Postgres 提供“记忆中心”基础读写服务。
- 前端：React + React Router 提供一个轻量控制台，用来：
  - 植入（创建）记忆；
  - 查询 / 筛选 / 分页浏览记忆；
  - 为未来 RAG / Profiles 等模块预留导航和 API 层。

---

## 2. 后端 Memory Service 设计

### 2.1 记忆模型 `Memory`

文件：`backend/memory/models/memory.py`

核心字段：

- `id: int` 主键，自增。
- `user_id: str | None` 用户 ID（可空）。
- `agent_id: str | None` Agent ID（可空）。
- `project_id: str | None` 项目 ID（可空）。
- `type: str` 记忆类型：`working` / `episodic` / `semantic`。
- `source: str` 来源标记：如 `system` / `user` / `agent` 等。
- `text: str` 记忆的原始文本内容。
- `summary: str | None` 摘要（预留给后续“反思 / 总结”能力）。
- `importance: float` 重要度（0~1）。
- `emotion: str | None` 情绪标签（预留）。
- `tags: JSONB | None` 标签数组或结构，JSONB 存储。
- `extra_metadata: JSONB | None`
  - 数据库列名为 `metadata`，ORM 字段名改为 `extra_metadata`，避免与 SQLAlchemy 保留字冲突。
- `created_at: datetime` 创建时间（服务器自动默认 `now()`）。
- `last_access_at: datetime | None` 最近访问时间（预留给后续“记忆检索更新”）。
- `recall_count: int` 被检索次数（初始 0）。

关键实现要点：

- 使用 `JSONB` 存储 `tags` 与 `metadata`，适合灵活的 KV / 数组结构。
- 将 ORM 字段名改为 `extra_metadata`，`mapped_column("metadata", JSONB...)` 指向底层列名 `metadata`，避免 `metadata` 与 `Base.metadata` 冲突。

### 2.1.1 三类核心记忆类型：`working` / `episodic` / `semantic`

`Memory.type` 字段当前约定三种核心取值，它们在整个系统中的“职责”不同：

- **`working` 工作记忆**
  - 含义：
    - 近几轮对话中的“短期工作上下文”，例如当前子任务、当前编辑的文件、当前推理中间结果等。
  - 特点：
    - 生命周期短，更多是“当前会话的 scratchpad”；
    - 在实现上分为三层：Agent 进程内的运行时 working、上游应用内部的会话级缓存（如 Redis）、以及 Memory Service 所管理的 DB 中 `type='working'` 快照；
    - 本项目的 Memory Service 与控制台**只负责管理数据库中的 `type='working'` 记录**，不直接连接或展示 Redis 等运行时缓存；
    - importance 一般偏低。
  - 适用场景示例：
    - 多轮推理中，记录“上一步已经检查过哪些文件”；
    - 当前正在执行的 TODO 子任务列表快照。

- **`episodic` 情节记忆（总结记忆）**
  - 含义：
    - 某一段时间 / 某一次会话 / 某个任务过程的“事件级总结”，回答“这一次主要发生了什么”。
  - 特点：
    - 通常由一段对话结束后，通过 LLM 自动生成；
    - 文本一般是 1~数段话，描述过程和关键决策；
    - 通过 tags/metadata 绑定 `session_id`、消息范围、job_id 等来源信息。
  - 适用场景示例：
    - “2025-12-03 晚上，用户和助手一起设计了记忆流水线和 Job 表结构。”
    - “本次会话完成了前端 Memory 控制台从单页到创建/查询双页的拆分。”
  - **当前实现进度**：
    - 已有 `Memory.type = 'episodic'` 的写入逻辑（通过 `/jobs/<id>/run` 的 MVP mock）；
    - Job 表 `memory_generation_jobs` 已建模，下一步会接入真实 LLM（deepseek-v3.2-exp）生成总结文本。

- **`semantic` 语义记忆（长期事实/偏好）**
  - 含义：
    - 稳定的事实、设定、用户偏好和项目知识，回答“这个用户/项目一贯是怎样的”。
  - 特点：
    - 倾向于“结论型的一句话”，例如：“用户偏好：回答时先给结论再解释。”；
    - 来源既可以是用户手动植入（前端创建页），也可以是 LLM 从对话中自动抽取；
    - importance 一般高于工作记忆，可能用于驱动人格画像（Profiles）。
  - 适用场景示例：
    - 用户的语言偏好、回答风格、常用技术栈；
    - 某个项目的长期约定（数据库选型、命名规范等）。

- **`semantic_extract` Job 的设计思路**：
  - 通过 `memory_generation_jobs` 中的 `job_type = 'semantic_extract'`，对某段 `conversation_messages` 运行一次“长期记忆抽取”：
    - 后端使用 `generate_semantic_memories(session_id, conversation_text)` 调用 LLM；
    - Prompt 会明确要求按上面的**画像维度**提取 0~N 条结论；
    - LLM 输出一个 JSON 数组，每个元素形如：
      - `{ "text": "一句话结论", "category": "communication", "tags": ["preference", "communication"] }`。
  - 每条输出会被转换为一条 `Memory(type='semantic')`：
    - `source = 'auto_semantic_extract'`；
    - `tags` 至少包含：`"semantic_auto"` 和 `"category:<category>"`；
    - `extra_metadata` 记录 `job_id / session_id / message 范围 / category`，保证可追溯。

- **Profiles 层（画像）的关系**：
  - Profiles 不再是单独的一套系统，而是构建在 `semantic`/`episodic` 之上的“聚合视图”：
    - 定期（或按需）收集某个 `user_id`（以及可选 `project_id`）下的高重要度 `semantic` 记忆；
    - 按 category 聚合为结构化画像 JSON（例如：communication / interest / risk / tools / lifestyle 等字段）；
    - 保存到单独的 `profiles` 表中，用于推理时注入 system prompt 或作为外部配置；
    - 当 Profiles 与底层记忆不一致时，以 `memories` 为权威来源，重新聚合。
  - 这样可以保证：
    - 日常检索 / RAG 直接使用 `memories`（semantic + episodic）；
    - 人格画像只是这些记忆的一个上层投影，随记忆演化而不断更新，而不是一套割裂的“平行人格系统”。

### 2.1.3 Profiles 聚合子模块设计（基于记忆的人格系统）

在上文中，`semantic` 已经被定义为“事实 / 偏好 / 设定 / 人物关系”等长期语义记忆，Profiles 只是构建在这些记忆之上的**视图层**，而不是一套独立的人格系统。本节描述 Profiles 聚合模块的实现思路与与 Memory 的关系。

#### 2.1.3.1 模块位置与职责边界

- 代码组织：
  - 与 `backend/memory` 并列新增 `backend/profiles` 子目录：
    - `models/profile.py`（可选）：定义 `Profile` ORM 模型；
    - `routes/profiles.py`：画像相关 REST API；
    - `services/profile_aggregate.py`：从 `Memory` 中抽取 & 聚合画像的业务逻辑；
  - 与 Memory Service 运行在同一进程中，共享同一套数据库连接与 LLM client。
- 职责：
  - **不直接管理底层记忆**（不写入 `memories` 表）；
  - 只负责：
    - 从 `memories` 中读取 `semantic` / `episodic`；
    - 调用 LLM 将其聚合为结构化画像 JSON；
    - 提供上游“按用户/项目加载画像”的查询接口。

这样可以保证：底层事实仍以 `memories` 为唯一权威来源，Profiles 只是其一个“投影 / 抽象层”，出现不一致时可以随时重建。

#### 2.1.3.2 Profile 数据结构（概念）

一个 Profile 可以看作是一个按维度划分的 JSON 对象，示例：

```jsonc
{
  "user_id": "u_123",
  "project_id": "proj_memRagAgent", // 可空，表示全局画像
  "communication_style": {
    "tone": "鼓励式，偏直接给结论",
    "language": "中文为主，偶尔掺杂英文术语"
  },
  "interests": [
    "Agent 架构设计",
    "RAG 与记忆系统结合"
  ],
  "risk_preference": "在技术选型上偏稳健，但愿意尝试新模型",
  "tools_and_habits": [
    "Windows 开发环境",
    "喜欢有清晰文档和 TODO 列表"
  ],
  "social_relations": [
    "与某助手长期协作，偏向 pair programming 模式"
  ],
  "project_facts": {
    "memRagAgent": {
      "stack": "Flask + Postgres + React",
      "design_principles": ["记忆可追溯", "模块化", "自进化能力"]
    }
  }
}
```

实现时可以将该 JSON 直接存入一个 `profiles` 表的 `profile_json` 字段中，或完全不建表，仅在需要时现算（代价更高）。

#### 2.1.3.3 画像聚合 Job 设计

为复用已有 Job 思路，Profiles 聚合也采用“Job 驱动”的方式：

- Job 来源：
  - 可以新增专门的 `profiles_jobs` 表；
  - 或在现有 `memory_generation_jobs` 中增加一种 `job_type = 'profile_aggregate'`；
  - 本项目更倾向于后者，保持统一 Job 表：
    - `job_type = 'profile_aggregate'`；
    - `target_types` 可以为空或标记为 `['profile']` 以示区分。
- Job 关键字段：
  - `user_id`（必填）；
  - 可选 `project_id`（仅聚合某个项目下的画像）；
  - `status` / `error_message` 等与其他 Job 一致。

执行流程（MVP）：

1. 创建 Job：
   - 上游或控制台触发 `POST /api/profiles/jobs`，指定 `user_id`（和可选 `project_id`）；
   - 后端在 `memory_generation_jobs` 中插入一条 `job_type='profile_aggregate'` 的记录。
2. 执行 Job：
   - 通过 `POST /api/profiles/jobs/<id>/run`（或统一的 `/api/memory/jobs/<id>/run`），在 worker 中执行：
     1. 查询该 `user_id`（和 `project_id`）下的 `semantic` 记忆，必要时补充少量高重要度 `episodic`；
     2. 将这些记忆（含 `text` / `tags` / `importance` 等）连同聚合模板一并传给 LLM；
     3. 要求 LLM 输出一个结构化 Profile JSON（见上小节）；
     4. 将该 JSON 写入 `profiles` 表（若存在则覆盖），并在 `extra_metadata` 中记录参与聚合的 memory_ids 与 job_id；
     5. 将 Job 状态置为 `done`，失败时记录 `error_message`。

#### 2.1.3.4 Profiles 查询 API 与上游使用方式

- 后端 API 形态：
  - `GET /api/profiles/<user_id>`：加载某用户的最新画像；
    - 可接受 `project_id` 作为查询参数，用于获取项目级画像；
  - 返回结构示例：

    ```jsonc
    {
      "user_id": "u_123",
      "project_id": "proj_memRagAgent",
      "profile": { /* 上文 profile_json 内容 */ },
      "updated_at": "2025-12-04T12:34:56Z"
    }
    ```

- 上游调用方式：
  - 在新建 Agent 或启动新对话时：
    1. 首先调用 `GET /api/profiles/<user_id>` 注入画像；
    2. 结合 `semantic` / `episodic` / `working` 的 Memory-RAG 结果，一起构造 LLM 的 system prompt 与检索上下文；
  - 当底层记忆发生重要变化（新增大量 semantic / 多次对话后）：
    - 通过控制台或后台任务触发 `profile_aggregate` Job，刷新画像。

#### 2.1.3.5 自进化与画像的关系

- Profiles 本身不直接“学习”，而是依赖底层记忆的自进化：
  - semantic / episodic 随对话与 Job 不断生成与更新；
  - 定期的聚合 Job 重新扫描这些记忆，生成新的画像；
- 当记忆层执行“强化 / 合并 / 淘汰”等自优化策略时：
  - Profiles 在下一次聚合时会自然反映这些变化（例如：兴趣从 A 渐渐转向 B，旧偏好被新记忆覆盖）。

因此，画像系统是“挂在记忆中心之上的演化视图”，而不是独立成长的一棵树，这保证了：

- **可追溯性**：任何画像结论都能追溯到具体 semantic / episodic 记忆；
- **一致性**：当画像与某条记忆冲突时，以记忆为准，通过再次聚合修正画像；
- **易扩展**：未来可根据需要增加新的画像维度，只需在聚合 prompt 与 Profile JSON 结构中扩展字段。

#### 2.1.3.6 记忆生成 & Profiles Job 总体流程（含 env 控制点）

这一小节用一个逻辑草图，把“对话 → 记忆 → 画像”的 Job 流和全局 env 控制点串起来，便于整体理解，也方便后续调优成本。

```mermaid
flowchart TD
  A[对话进行中\nconversation_messages] --> B[会话结束 / 定时触发]

  B --> C[创建 Job\n- episodic_summary\n- semantic_extract\n- profile_aggregate]
  C --> D[Job 表\nmemory_generation_jobs\nstatus=pending]

  subgraph Scheduler[嵌入进程 Job 调度器\n(app.py 中的后台线程)
  ]
    E[读取 env\nJOB_SCHEDULER_ENABLED\nJOB_RUN_WINDOW_*] --> F[判断当前时间\n是否落入各 job_type 的执行窗口]
    F --> G[按类型拉取 pending Job\n调用 /api/memory/jobs/<id>/run]
  end

  D --> Scheduler
  G --> H[run_job(job_id) 内部逻辑]

  H --> H1[按 job_type 选择分支\n- episodic_summary\n- semantic_extract\n- profile_aggregate]
  H1 --> H2[写入 Memory / Profiles 等结果\n并更新 job.status]

  subgraph Profiles[Profiles 子系统]
    S1[Memory(type='semantic')] --> P1[聚合画像\nprofiles.profile_json]
    P1 --> P2[旧版本写入\nprofiles_history]
  end

  H2 --> S1
```

关键控制点说明：

- **Job 创建层**（触发条件）
  - `episodic_summary` / `semantic_extract`：
    - 目前主要通过前端 Jobs 控制台或上游服务“手动创建 Job”；
    - 未来可以在 `conversation_sessions` 的“会话关闭”操作中，依据 `auto_episodic_enabled` / `auto_semantic_enabled` 自动插入 Job。
  - `profile_aggregate`：
    - 手动创建：`POST /api/memory/jobs/profile`；
    - 自动创建：`POST /api/memory/jobs/profile/auto`，根据“新增 semantic 条数”决定是否创建画像 Job，默认阈值由 env `PROFILE_AUTO_JOB_MIN_NEW_SEMANTIC` 控制（可被单次请求覆盖）。

- **画像查询层**（在线刷新 vs 缓存命中）
  - API：`GET /api/profiles/<user_id>?project_id=...&force_refresh=...`。
  - 默认行为：
    - 若存在缓存画像且未显式 `force_refresh=true`，优先返回缓存；
    - 若 `PROFILE_AUTO_REFRESH_ENABLED=true`，同时会检查自 `profiles.updated_at` 以来新增的 `semantic` 条数是否达到 `PROFILE_MIN_NEW_SEMANTIC_FOR_REFRESH`，满足时本次请求会自动调用 LLM 重新聚合画像并更新缓存。
  - 成本控制：
    - 关闭在线自动刷新：`PROFILE_AUTO_REFRESH_ENABLED=false` → 只在 `force_refresh=true` 或缓存缺失时调用 LLM。
    - 调整在线刷新灵敏度：通过 `PROFILE_MIN_NEW_SEMANTIC_FOR_REFRESH` 增大/减小阈值。

- **调度执行层（嵌入进程线程）**
  - 行为：在 `backend/memory/app.py` 中启动一个后台线程，循环：
    - 读取当前时间；
    - 对三类 job_type：
      - `episodic_summary` → `JOB_RUN_WINDOW_EPISODIC`
      - `semantic_extract` → `JOB_RUN_WINDOW_SEMANTIC`
      - `profile_aggregate` → `JOB_RUN_WINDOW_PROFILE`
    - 落入相应时间窗口时：查询少量 `status='pending'` 的 Job，并通过 REST `POST /api/memory/jobs/<id>/run` 触发执行。
  - 全局开关：
    - `JOB_SCHEDULER_ENABLED=false` 时，调度线程不启动，所有 Job 仅在手动点击“执行”时运行。
  - 成本与节奏：
    - 可以把所有自动 Job 安排在夜间窗口执行，例如：
      - `JOB_RUN_WINDOW_EPISODIC=02:00-05:00`
      - `JOB_RUN_WINDOW_SEMANTIC=02:00-05:00`
      - `JOB_RUN_WINDOW_PROFILE=03:00-06:00`

- **Profiles 自进化与版本管理**
  - `profile_aggregate` Job 分支在 `run_job` 中：
    - 汇总高重要度的 `semantic` 记忆调用 LLM 聚合画像；
    - 若存在旧画像，则先把旧 `profile_json` 记录到 `profiles_history`（自增 version），再覆盖 `profiles` 当前值；
    - 这样可以在控制台里回溯画像演化过程，支撑“自进化可解释性”。

#### 2.1.3.7 会话关闭 + 消息数阈值下的自动 Job 创建

在前文中，Job 的创建主要依赖两条路径：

- 手动在控制台 / 上游服务中调用：
  - `POST /api/memory/jobs/episodic`
  - `POST /api/memory/jobs/semantic`
  - `POST /api/memory/jobs/profile`
- 定时 / 事件触发调用：
  - `POST /api/memory/jobs/profile/auto`

为了让“对话结束时”自动生成合适的记忆，本项目增加了：

- `conversation_sessions` 表中的三个位开关：
  - `auto_episodic_enabled BOOLEAN DEFAULT TRUE`
  - `auto_semantic_enabled BOOLEAN DEFAULT TRUE`
  - `auto_profile_enabled  BOOLEAN DEFAULT FALSE`
- 会话关闭 API：`POST /api/memory/sessions/<session_id>/close`

关闭逻辑（MVP）：

- 根据 `session_id` 查找 `conversation_sessions`：
  - 若不存在 → 404；
  - 若 `status='closed'` → 返回 `status=already_closed`.
- 否则：
  - 将 `status` 置为 `closed`，`closed_at = now()`；
  - 统计该会话的消息条数：
    - `msg_count = COUNT(conversation_messages WHERE session_id=...)`.
  - 从 env 读取消息数阈值：
    - `EPISODIC_AUTO_MIN_MESSAGES`（默认 3）；
    - `SEMANTIC_AUTO_MIN_MESSAGES`（默认 5）；
    - `PROFILE_AUTO_MIN_MESSAGES`（默认 10）.
  - 若 `auto_episodic_enabled=true` 且 `msg_count >= EPISODIC_AUTO_MIN_MESSAGES`：
    - 自动创建一条 `job_type='episodic_summary'`、`target_types=['episodic']` 的 Job；
  - 若 `auto_semantic_enabled=true` 且 `msg_count >= SEMANTIC_AUTO_MIN_MESSAGES`：
    - 自动创建一条 `job_type='semantic_extract'`、`target_types=['semantic']` 的 Job；
  - 若 `auto_profile_enabled=true` 且 `msg_count >= PROFILE_AUTO_MIN_MESSAGES`：
    - 为该 `user_id + project_id` 创建一条 `job_type='profile_aggregate'` 的 Job.

返回值中会携带：

- `message_count`：本次会话累计消息数；
- `episodic_min_messages` / `semantic_min_messages` / `profile_min_messages`：本次使用的阈值；
- `created_jobs`：实际创建的 Job 列表（含 job_type / session_id / user_id / project_id）。

这样可以保证：

- 短会话不会因为零星几条消息就产生大量 episodic / semantic 总结任务；
- 每条会话可以按需配置“关闭时是否自动生成总结 / 语义记忆 / 画像 Job”。

### 2.1.4 `tags` 字段的设计原则与自优化

`Memory.tags` 使用 JSONB 存储，用于给记忆打上多个维度的标签，便于筛选和后续 RAG / 画像聚合。建议遵循以下原则：

- **统一格式**：
  - 全部使用小写、短横线或冒号分隔：如 `"preference"`、`"project:memRagAgent"`、`"type:episodic"`；
  - 避免在 tag 字符串中混入空格和中文标点。

- **分层命名**：
  - 主题类：`"preference"`、`"profile"`、`"session_summary"`；
  - 作用域类：`"project:memRagAgent"`、`"user:u_123"`；
  - 类型类：`"type:semantic"`、`"type:episodic"`；
  - 来源类：`"source:auto"`、`"source:manual"`。

- **最小必要集合**：
  - 每条记忆保持少量高价值标签（1~5 条），避免 tag 爆炸；
  - 通过 importance / usage 决定是否补充更多细粒度标签。

- **自优化思路**：
  - 后台任务可以定期根据已有记忆的 `text` / `metadata` 自动补充统一风格的标签：
    - 例如，对所有 `type='episodic'` 的记忆统一加上 `"type:episodic"`；
    - 对包含某些关键词（如“偏好”、“喜欢”）的记忆加上 `"preference"`；
  - 检测到重复或含义接近的标签（如 `"profile"` / `"profiles"`）时，可以统一归一。

- **检索策略配合**：
  - 当前控制台查询页默认按 `types=['semantic','episodic']` 检索；
  - 标签筛选框传入的字符串会拆分为数组匹配 `tags`，后端用 `ILIKE` 在 JSONB 串中做简单包含过滤；
  - 未来可在 RAG 层使用向量 + tag 组合过滤（先按 tag 粗筛，再做相似度搜索）。

通过遵守上述命名和归一原则，可以在不引入复杂索引结构的前提下，逐步让 `tags` 成为“可搜索、可聚合、可解释”的重要维度。

### 2.2 数据库会话与环境变量

文件：`backend/memory/repository/db_session.py`

- 使用 `python-dotenv` 加载 `.env`：
  - `POSTGRES_HOST`
  - `POSTGRES_PORT`
  - `POSTGRES_DB`
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`
- 基于上述变量拼接 Postgres 连接串。
- 提供：
  - `engine`：SQLAlchemy Engine。
  - `SessionLocal`：用于在路由中 `db = SessionLocal()` 获取会话。
  - `init_db()`：在应用启动时初始化（创建表等）。

`backend/memory/app.py` 中：

- 导入并调用 `init_db()`，确保启动时数据库结构就绪。
- 注册 `memory_bp` Blueprint，将 `/memories` 相关路由挂载到应用。
- 提供 `GET /health` 做健康检查。

### 2.3 创建记忆接口 `POST /memories`

文件：`backend/memory/routes/memories.py`

- 路由：`@memories_bp.post("/memories")`
- 输入 JSON（核心字段）：
  - `user_id` / `agent_id` / `project_id`
  - `type`（默认为 `semantic`）
  - `source`（默认为 `system`）
  - `text`（必填）
  - `importance`（默认 0.5）
  - `emotion`
  - `tags`（任意 JSON）
  - `metadata`（任意 JSON → ORM 字段 `extra_metadata`）
- 逻辑：
  1. 从 `request.get_json()` 中取参数。
  2. 校验 `text` 必填，否则 400。
  3. 构造 `Memory` 实例并写入数据库，`db.commit()` + `db.refresh()` 获取自增 ID 等信息。
  4. 返回 201 JSON，字段名对外保持 `metadata`，内部映射为 `extra_metadata`。

这为“植入记忆”提供了后端能力。

### 2.4 查询记忆接口 `POST /memories/query`

文件：`backend/memory/routes/memories.py`

#### 2.4.1 请求体设计

核心字段：

- 顶层：
  - `user_id` / `project_id`
  - `query`: 文本模糊搜索内容（对 `text` 做 `ILIKE`）。
  - `top_k`: int
    - 若 > 0：表示最多取前 N 条结果；
    - 当前控制台模式中设为 0，完全交给分页控制数量。
  - `page`: 页码，从 1 开始，默认 1。
  - `page_size`: 每页数量，默认 10，最大 100。
- `filters` 对象：
  - `types`: `['semantic', ...]` 按记忆类型过滤。
  - `min_importance`: 最小重要度（float）。
  - `tags`: 标签列表，按 JSONB 字符串包含过滤。

#### 2.4.2 过滤与分页逻辑

1. 基础 Query
   - `q = db.query(Memory)`。
   - 按条件依次过滤：
     - `user_id` / `project_id` 精确匹配。
     - `types` → `Memory.type.in_(types)`。
     - `min_importance` → `Memory.importance >= min_imp`。
     - `tags`：
       - 由于 `tags` 是 JSONB，使用 `cast(Memory.tags, TEXT).ilike("%tag%")` 简易包含过滤。
     - `query_text`：
       - `Memory.text.ilike("%query_text%")`。

2. 先计算总数
   - `total = q.count()`。

3. 排序
   - 按 `importance` 降序 + `created_at` 降序：
   - `q = q.order_by(Memory.importance.desc(), Memory.created_at.desc())`。

4. 分页与 `top_k` 协调
   - 约束 `page` 与 `page_size` 合法范围。
   - 若 `top_k > 0`，则实际使用的 `effective_page_size = min(page_size, top_k)`；否则直接用 `page_size`。
   - `offset = (page - 1) * effective_page_size`。
   - `q = q.offset(offset).limit(effective_page_size)`。

5. 构造返回值

返回结构：

```jsonc
{
  "items": [
    {
      "memory": { /* Memory 字段 */ },
      "score": 0.95  // 当前用 importance 作为得分
    }
  ],
  "page": 1,
  "page_size": 10,
  "total": 57,
  "has_next": true,
  "has_prev": false
}

487→这既适合管理控制台分页，也可以满足后续 Agent / RAG 侧基于 `top_k` 的快速检索需求。
488→
489→---

### 2.5 上游调用 `/memories/query` 的推荐记忆组合（Cookbook）

为了让上游聊天 / Agent / 其他服务更好地利用 Memory Service，这里给出几种常见场景下的“推荐记忆组合”，作为调用 `/memories/query` 的参考范式。

#### 2.5.1 普通对话轮次：提供上下文而不过载
### 3.1 HTTP 与 API 抽象层

#### 3.1.1 通用 HTTP 封装 `api/http.ts`

目标：统一处理：

- 基础 URL / headers 设置；
- 请求 JSON 序列化和响应 JSON 解析；
- 错误抛出（非 2xx 状态抛出异常）。

这样上层业务 API（memory / rag / profiles）只关注：

- URL 路径；
- 请求体结构；
- 响应类型。

#### 3.1.2 Memory API `api/memory.ts`

对后端接口的封装：

- `fetchMemoryHealth()` → `GET /api/memory/health`。
- `createMemory(payload)` → `POST /api/memory/memories`。
- `queryMemories(payload)` → `POST /api/memory/memories/query`，支持：
  - `page` / `page_size` / `top_k`；
  - `filters`（types / tags / min_importance）。

同时定义了：

- `HealthResponse` 类型；
- `CreateMemoryPayload` 类型；
- `QueryMemoriesPayload` 与 `QueryMemoriesResponse` 类型；
- `QueryResultItem`（每条记录包含 `memory` + `score`）。

#### 3.1.3 RAG / Profiles API 占位

- `api/rag.ts`：定义 `RagQueryPayload` / `RagQueryResponse`，提供 `ragQuery()` 函数（目前调用到暂未实现的后端 RAG 接口）。
- `api/profiles.ts`：定义 `Profile` 类型和简单加载函数，占位未来用户画像系统。

### 3.2 路由与布局 `App.tsx`

- 使用 `BrowserRouter` + `Routes`：
  - `/` → 重定向到 `/memories/create`。
  - `/memories/create` → `MemoryCreatePage`（创建记忆）。
  - `/memories/query` → `MemoryQueryPage`（查询记忆）。
  - `/rag` → `RagPage`（占位）。
  - `/profiles` → `ProfilesPage`（占位）。

- 顶部导航：
  - “创建记忆” → `/memories/create`
  - “查询记忆” → `/memories/query`
  - “RAG” → `/rag`
  - “Profiles” → `/profiles`

- 布局风格：
  - 顶部 Header：项目标题 + 导航菜单。
  - 主体为卡片式 Section，适合控制台场景。

---

## 4. 记忆控制台页面拆分：创建 vs 查询

### 4.1 设计原因

最初页面是“创建 + 查询”合在一个页面中，随着功能丰富：

- 创建表单本身字段较多，且还有健康检查信息；
- 查询部分需要分页、表格展示、将来可能扩展编辑 / 删除 / 打标签等操作；

合在一起会使单页面：

- 职责不清晰；
- UI 纵向过长；
- 后续扩展难以维护。

因此将 Memory 控制台拆成 **两套页面**：

- `MemoryCreatePage`：专注“植入记忆”。
- `MemoryQueryPage`：专注“查询 + 分页浏览 + 管理记忆”。

### 4.2 创建记忆页 `MemoryCreatePage.tsx`

路由：`/memories/create`

功能：

1. 健康检查
   - 使用 `fetchMemoryHealth()` 调用后端 `GET /health`。
   - 显示状态 / 服务名 / 版本，无法获取时显示中文错误提示。

2. 植入记忆表单
   - 字段：
     - 用户 ID（默认示例：`u_123`）。
     - 项目 ID（默认示例：`proj_memRagAgent`）。
     - 记忆类型：`semantic` / `episodic` / `working`。
     - 记忆内容 `text`（多行）。
     - 标签 `tags`（输入框，逗号分隔）。
   - 提交逻辑：
     - 将标签按逗号分割为数组，过滤空字符串。
     - 调用 `createMemory()`，传入 `user_id` / `project_id` / `type` / `source` / `text` / `importance` / `tags`。
     - 调用成功后：
       - 显示“记忆已成功写入。”
       - 清空内容输入框。
     - 调用失败：
       - 显示“写入失败: xxx” 中文错误信息。
   - UX 提示：
     - 一条中文建议：鼓励用户对语义记忆写出“结论型的一句话”，方便后续 Agent 进行检索与应用。

### 4.3 查询记忆页 `MemoryQueryPage.tsx`

路由：`/memories/query`

功能：

1. 健康检查
   - 与创建页相同，保证两页都能快速看到服务是否正常。

2. 查询条件表单
   - 字段：
     - 用户 ID（默认：`u_123`）。
     - 项目 ID（默认：`proj_memRagAgent`）。
     - 查询内容 `query`：对 `text` 做模糊匹配。
     - 标签筛选：逗号分隔，映射到 `filters.tags`。
   - 提交后：
     - 调用 `queryMemories()`：
       - `user_id` / `project_id`
       - `query`
       - `top_k = 0`（完全交给分页控制数量）。
       - `page = 1`，`page_size = 10`。
       - `filters.types = ['semantic']`（当前示例默认查语义记忆，可后续做成下拉多选）。
       - `filters.tags = [...]`。

3. 分页与结果展示

- 状态管理：
  - `page` / `pageSize` / `total` 用于分页。
  - `qItems: QueryResultItem[]` 存放当前页结果。
  - `qLoading` / `qError` 用于请求状态。
- 表格展示：
  - 列：
    - ID
    - 类型
    - 重要度
    - 内容
    - 标签（数组 join 成字符串）
    - 创建时间
- 分页条（中文）：
  - `第 {page} 页 / 共 {Math.max(1, ceil(total / pageSize))} 页，合计 {total} 条`
  - `上一页` / `下一页` 按钮：
    - 前一页：`page > 1` 时生效，调用 `runQuery(page - 1)`。
    - 后一页：`page * pageSize < total` 时生效，调用 `runQuery(page + 1)`。

这种设计使得：

- **创建页** 专心写入数据；
- **查询页** 专心做“读 + 管理”；
- 未来在查询页可以继续扩展：删除 / 编辑 / 重要度调整 / 标签维护等操作，而不会污染创建流程。

---

## 5. 记忆流水线与 Job 设计（对话 → 记忆）

为了支持自动生成情节记忆（episodic summary）、语义记忆和后续人格画像，需要在 `memories` 表之外，补充：

- 原始对话层：记录“谁在什么会话里说了什么”。
- 触发 / Job 层：记录“在什么条件下、对哪段对话、生成什么类型的记忆”。

### 5.1 会话表 `conversation_sessions`

**作用**：描述一条“聊天目录 / 会话”的元信息，解决“同一个用户有多个会话”的问题。

核心字段（概念）：

- `session_id`：业务侧会话 ID（可与外部系统对齐），唯一。
- `user_id` / `agent_id` / `project_id`：标识这条会话属于谁、在哪个 Agent / 项目中发生。
- `title`：可选的会话标题（例如第一轮对话的摘要）。
- `status`：`active` / `closed`，会话是否仍在进行。
- `created_at` / `closed_at`：会话生命周期时间戳。

用途：

- 当会话从 `active` 变为 `closed` 时，可以触发一条“会话级的 episodic 总结 Job”。

> 具体建表 SQL 参考：`backend/memory/db/conversation_sessions.sql`

### 5.2 消息表 `conversation_messages`

**作用**：记录每一条原始对话消息，是自动生成记忆的“原料层”。

核心字段（概念）：

- `id`：自增 message_id，便于按范围选取一段对话。
- `session_id`：隶属的会话 ID，对应 `conversation_sessions.session_id`。
- `user_id` / `agent_id` / `project_id`：冗余字段，方便按人/项目过滤。
- `role`：`user` / `assistant` / `system` / `tool`。
- `content`：消息正文。
- `metadata`：JSONB，记录渠道、外部 message_id、调用来源等补充信息。
- `created_at`：消息时间戳。

用途：

- Job 在执行时，会根据 `session_id` + 消息范围，从这里提取需要传给 LLM 的消息片段。

> 具体建表 SQL 参考：`backend/memory/db/conversation_messages.sql`

### 5.3 Job 表 `memory_generation_jobs`

**作用**：只负责标记“什么时候、对谁、针对哪一段对话，去生成什么类型的记忆”，真正的 LLM 调用逻辑在 worker / 服务代码中实现。

核心字段（概念）：

- `user_id` / `agent_id` / `project_id`：本次生成记忆针对的用户 / Agent / 项目。
- `session_id`：本次生成记忆针对的会话。
- 消息范围：
  - `start_message_id` / `end_message_id`：
    - 表示只对该会话中 `[start_message_id, end_message_id]` 区间的消息做总结；
  - 或使用 `start_time` / `end_time` 描述时间窗口（二选一即可）。
- `job_type`：例如 `episodic_summary`（后续可扩展 `semantic_extract` 等）。
- `target_types`：例如 `['episodic']`，表示要写入 `memories` 中的记忆类型集合。
- `status`：`pending` / `running` / `done` / `failed`，便于 worker 轮询和监控。
- 时间戳：`created_at` / `updated_at`，以及可选的 `error_message` 记录失败原因。

执行流程（MVP，针对 episodic 总结）：

1. 在线对话系统检测到会话结束：
   - 将 `conversation_sessions.status` 置为 `closed`，填充 `closed_at`；
   - 创建一条 `memory_generation_jobs` 记录，`job_type = 'episodic_summary'`，`target_types = ['episodic']`，并指明 `session_id` 和消息范围。
2. 后台 worker 周期性扫描 `status='pending'` 的 job：
   - 将 job 状态改为 `running`；
   - 从 `conversation_messages` 中按 `session_id + 消息范围` 取出对话片段；
   - 调用 LLM 生成一条（或零条） episodic 总结；
   - 通过 `/memories` 接口写入一条 `type='episodic'` 的记忆，并在 `metadata` 中记录 `job_id` / `session_id` / `message_range`；
   - 成功后将 job 状态置为 `done`，出错则置为 `failed` 并写入错误信息。

> 具体建表 SQL 参考：`backend/memory/db/memory_generation_jobs.sql`

这种设计保证：
- 原始对话、记忆、Job 三个层次职责清晰；
- Job 表只描述“何时、对谁、对哪一段对话、生成什么类型的记忆”，而不耦合 LLM 细节；
- 后续扩展 `semantic_extract`、profile 聚合等，只需新增 `job_type` / `target_types` 和对应 worker 逻辑。

### 5.4 会话生命周期与重启恢复策略
在实际接入聊天/Agent 系统时，“当前会话是谁”“这次会话是否已经结束”“重启后还算不算同一个任务”是非常关键但容易混乱的问题。本小节约定 Memory Service 与上游应用在会话生命周期上的分工和最佳实践。

#### 5.4.1 职责边界：谁负责划分会话

- **上游应用负责管理 `session_id` 与会话状态**：
  - 创建会话：生成业务侧 `session_id`，在 `conversation_sessions` 中插入一行，`status='active'`；
  - 继续对话：后续所有消息都带上同一个 `session_id`，落到 `conversation_messages`；
  - 显式结束：用户点击“结束对话”或业务逻辑判定任务完成时，将 `conversation_sessions.status` 置为 `closed` 并写入 `closed_at`；
  - 非显式结束（超时）：后台任务可以按配置（例如 30 分钟 / 2 小时无消息）自动将长时间未活跃的会话标记为 `closed`。
- **Memory Service 不自行“猜测当前会话”**：
  - 所有接口都依赖上游传入的 `session_id`；
  - 是否拆分为多个会话（如换页面、换任务）由业务侧决定。

1. **RAG 服务对接**
   - 在 `backend/rag` 下实现 RAG 路由与检索逻辑。
   - 与 Memory Service / 向量库 / 图数据库整合。
   - 前端 `RagPage` 替换为真实检索与可视化界面。

2. **Profiles / 用户画像中心**
   - 定义 Profile 模型（基础信息 + 偏好 + 历史行为摘要）。
   - 与 Memory Service 之间建立映射（如某些语义记忆自动归纳进用户画像）。

3. **记忆生命周期与反思机制**
   - 定时扫描重要记忆，生成抽象 / 总结写入 `summary` 或新语义记忆。
   - 根据 `recall_count` / `last_access_at` 做“遗忘曲线”或冷存储。

4. **前端交互增强**
   - 查询结果中的行内操作按钮（编辑、删除、标记重要）。
   - 更丰富的过滤条件（按时间范围 / 重要度区间）。
   - 导出功能（导出为 JSON/CSV）。

---

## 6. Memory-RAG 设计（初稿）

> 本节为后续“记忆增强检索 / 推理（Memory-RAG）”的设计草图，当前实现以 Memory Service + Profiles + 控制台为主，RAG 部分将逐步落地。

### 6.1 目标与角色分工

- **目标**：在已有 Memory & Profiles 之上，提供一个统一的“记忆检索 + 重排 + 注入 LLM”能力，满足：
  - 聊天 / Agent 推理时，从长期记忆中取出少量高价值上下文；
  - 支持按 user_id / project_id / session_id 做 scope 限定；
  - 支持 importance / recency / 画像偏好等因素综合排序；
  - 方便在前端控制台中调试“给定 query 时，被选中的记忆有哪些，为什么”。

- **角色分工**：
  - Memory Service：
    - 保存 working / episodic / semantic 记忆；
    - 提供结构化查询与 Job 流水线；
    - 负责生成 embeddings（未来）。
  - Profiles：
    - 从 semantic / episodic 聚合出画像 JSON，用于构造 system prompt 或过滤候选记忆。
  - RAG 子模块：
    - 在 Memory Service 内部或旁路服务中，完成“向量检索 + 规则过滤 + 重排”。

### 6.2 数据来源与向量存储（规划）

- **数据来源**：
  - `Memory.type='semantic'`：主要 RAG 召回来源（用户偏好 / 项目事实）。
  - `Memory.type='episodic'`：作为“最近一段会话的总结”，可选地加入 RAG（按 recency + importance 加权）。
  - Profiles：不直接参与向量检索，但会通过画像字段：
    - 影响 prompt（描述用户风格 / 项目背景）；
    - 未来可用于过滤候选记忆（例如：只取与某 project_facts 相关的记忆）。

- **向量存储方案（MVP 规划）**：
  - 为 Memory 新增 embedding 字段或单独建 `memory_embeddings` 表：
    - `memory_id` → 对应 `memories.id`；
    - `embedding` → 向量列（可用 Postgres + pgvector 或简单文件/内存索引）；
    - `created_at` / `updated_at`。
  - 在生成 semantic / episodic 时：
    - 同步或异步调用 embedding 模型（可与当前 LLM Client 复用或分离）；
    - 写入 / 更新向量表。

### 6.3 RAG 流水线（概念）

```mermaid
flowchart TD
  Q[上游请求\n(query + user_id + project_id + session_id)] --> F1[构造检索范围\n- 限定 user_id / project_id\n- 过滤 type in ['semantic','episodic']]

  F1 --> F2[向量检索\n- 生成 query embedding\n- 在向量表中做 top-k 近邻搜索]

  F2 --> F3[规则过滤\n- 按 importance / recency / tags 过滤\n- 可选：按 Profiles 中的 project_facts 过滤]

  F3 --> F4[重排\n- 结合相关度 / importance / recency\n- 控制最终返回数量]

  F4 --> F5[构造 LLM 上下文\n- 拼接选中的 Memory 文本\n- 加入 Profiles 的关键信息\n- 返回给上游用于构造 prompt]

## 7. 总结

本次骨架实现的核心成果：

1. **后端 Memory Service**：
   - 统一的 `Memory` 模型，兼顾结构化字段和 JSONB 灵活存储。
   - 提供 `POST /memories` 与 `POST /memories/query`，支持过滤与分页。
2. **前端记忆控制台**：
   - 抽象 `http.ts` + `memory.ts` 等 API 层，方便后续扩展 RAG / Profiles。
   - 使用 React Router 拆成两个独立页面：
     - 创建记忆：`/memories/create`
     - 查询记忆：`/memories/query`
   - 查询页支持服务健康状态展示、条件过滤和中文分页 UI。

这份文档可以作为后续开发（RAG、Profiles、多 Agent 集成）时的参考，也方便新人快速理解当前 Memory 控制台的设计与实现过程。
