# 知识库子系统设计说明（Knowledge Service）

> 目标：在现有 Memory Service 之外，新增一个面向各类“知识内容”的后端子系统，支持法律法规、心理学知识、企业邀约话术、医院专业术语等多领域知识的统一存储、索引与检索。
>
> 要求：
> - 不使用 kb 简写，命名直观；
> - 数据模型具备多领域可扩展性；
> - 与现有记忆服务解耦，但易于在编排层组合使用；
> - 方便后续对接文件监控 / 批量写库 / 图谱等能力。

---

## 1. 总体架构概览

当前整体架构分为三块：

- **Memory Service（个人记忆中心）**：
  - 面向用户会话：episodic / semantic / profile_aggregate；
  - 提供 `/api/memory/...` 与 `/api/rag/query`、`/api/memory/context/full`；
  - 存储在 `memories` + `memory_embeddings` + `profiles` 等表中。

- **Knowledge Service（知识库子系统）**：
  - 面向“客观知识内容”：法律条文、心理学条目、邀约话术、术语表等；
  - PostgreSQL 中使用 `knowledge_collections` / `knowledge_documents` / `knowledge_chunks` 三张表；
  - 独立 Flask App，路由前缀 `/api/knowledge`；
  - 后续可挂接 Chroma / Neo4j 做向量检索与图谱。

- **上游编排层 / Agent**：
  - 可以在一轮对话中，同时调用：
    - Memory Service 的 `/api/memory/context/full`（画像 + 最近对话 + 个人记忆）；
    - Knowledge Service 的 `/api/knowledge/...`（领域知识 RAG）；
  - 在 Prompt 中自行组合三类信息。

---

## 2. 数据模型设计（PostgreSQL）

### 2.1 knowledge_collections —— 知识集合

```sql
CREATE TABLE knowledge_collections (
    id               SERIAL PRIMARY KEY,
    project_id       VARCHAR(128),
    name             VARCHAR(256)        NOT NULL,
    domain           VARCHAR(64)         NOT NULL, -- law / psychology / sales_script / medical_terms ...
    description      TEXT,
    default_language VARCHAR(16),
    metadata         JSONB,
    created_at       TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);
```

设计要点：

- **project_id**：可选。支持：
  - 为空 → 全局共享知识库；
  - 有值 → 某个项目独享的知识集合。
- **domain**：领域标识，不限制取值，建议：
  - `law`：法律法规；
  - `psychology`：心理学；
  - `sales_script`：企业邀约话术；
  - `medical_terms`：医院术语；
  - 后续可自由扩展。
- **metadata (JSONB)**：领域无关的附加信息，如 `{"country": "CN", "industry": "medical"}`。

### 2.2 knowledge_documents —— 知识文档

```sql
CREATE TABLE knowledge_documents (
    id              SERIAL PRIMARY KEY,
    collection_id   INTEGER             NOT NULL REFERENCES knowledge_collections(id) ON DELETE CASCADE,
    external_id     VARCHAR(128),       -- 原系统中的标识，例如法条编号 / 文档 ID
    title           VARCHAR(512)        NOT NULL,
    source_uri      TEXT,               -- 文件路径或 URL
    metadata        JSONB,
    status          VARCHAR(32)         NOT NULL DEFAULT 'raw', -- raw / parsed / indexed
    created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);
```

设计要点：

- `collection_id`：归属于哪个知识集合。
- `external_id`：方便同外部系统（原有知识库、法条编号等）做映射。
- `status`：
  - `raw`：仅登记了文档元信息；
  - `parsed`：已完成文本抽取或结构化解析；
  - `indexed`：已完成 chunk + embedding 写入。
- `metadata`：存放与文档级别相关的信息，例如：
  - 法律：`{"law_code": "劳动法", "publish_date": "2023-01-01"}`；
  - 心理学：`{"topic": "依恋理论"}`；
  - 医院术语：`{"department": "cardiology"}`。

### 2.3 knowledge_chunks —— 知识片段（RAG 基本单元）

```sql
CREATE TABLE knowledge_chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER             NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER             NOT NULL,
    section_label   VARCHAR(256),       -- 例如 "第三章 第十条"、"第 3 段"
    text            TEXT                NOT NULL,
    tags            JSONB,              -- 通用标签：主题、适用范围、学科等
    embedding       JSONB,              -- 暂用 JSONB 存储向量数组，后续可切换 pgvector
    importance      FLOAT               DEFAULT 0.5,
    metadata        JSONB,
    created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);
```

设计要点：

- **document_id + chunk_index**：唯一标识一个片段在文档中的顺序；
- **section_label**：对人类友好的位置说明（章节/条文/段落）；
- **tags**：灵活打标签，例如：
  - 法律：`{"topic": "解除劳动合同", "applicable_group": "employee"}`；
  - 心理学：`{"theory": "attachment", "level": "intro"}`；
- **embedding (JSONB)**：先沿用 JSON 数组，未来可以改为 pgvector 类型；
- **metadata**：片段级元信息，与 `tags` 互补（可放更结构化的数据）。

ORM 模型中，为避免与 SQLAlchemy 保留字冲突，所有 `metadata` 列字段在 Python 属性上命名为 `extra_metadata`。

---

## 3. 已实现的后端路由（Flask /api/knowledge）

在 `backend/knowledge/app.py` 中：

```python
app.register_blueprint(knowledge_bp, url_prefix="/api/knowledge")
```

当前 `routes/knowledge.py` 已提供的接口：

### 3.1 认证说明

所有 API 请求需要携带认证头（生产模式下）：

| Header | 说明 | 必填 |
|--------|------|------|
| `X-API-Key` | API 密钥 | 是（生产模式） |
| `X-Project-Id` | 项目/租户编码 | 否（管理员可不填） |

详细认证机制参见 [TENANT_SECURITY.md](./TENANT_SECURITY.md)。

### 3.2 健康检查

- `GET /api/knowledge/health`
  - 返回：`{"status": "ok", "service": "knowledge", "version": "0.1"}`。

### 3.2 知识集合管理

- `POST /api/knowledge/collections`

  ```jsonc
  {
    "project_id": "proj_law_demo",   // 可选
    "name": "中国法律法规",          // 必填
    "domain": "law",               // 必填
    "description": "法律法规与司法解释",
    "default_language": "zh-CN",
    "metadata": {"country": "CN"}
  }
  ```

- `GET /api/knowledge/collections?project_id=...&domain=...`
  - 支持按 `project_id` / `domain` 过滤。

### 3.3 文档管理

- `POST /api/knowledge/documents`

  ```jsonc
  {
    "collection_id": 1,              // 必填
    "external_id": "LABOR_LAW_2024",
    "title": "劳动合同法（2024 修订版）", // 必填
    "source_uri": "file:///.../labor_law_2024.pdf",
    "metadata": {
      "law_code": "劳动合同法",
      "publish_date": "2024-01-01"
    }
  }
  ```

- `GET /api/knowledge/documents?collection_id=1&status=indexed`
  - 按集合 / 状态过滤。

### 3.4 Chunk 查看

- `GET /api/knowledge/documents/<document_id>/chunks`
  - 返回指定文档下的所有片段（不含 embedding 字段，便于控制台查看）。

### 3.5 文档索引

- `POST /api/knowledge/documents/<id>/index`
  - 将指定文档做抽取+分块+embedding 写入 `knowledge_chunks`；
  - 支持 JSONL / JSON / txt / pdf / docx 等格式。

### 3.6 RAG 查询

- `POST /api/knowledge/rag/query`

  ```jsonc
  {
    "project_id": "proj_law_demo",      // 可选
    "collection_ids": [1, 2],           // 可选，限定集合
    "domain": "law",                    // 可选，按领域过滤
    "query": "解除劳动合同的补偿标准是什么？",
    "top_k": 8,
    "required_tags": ["劳动合同"],      // 可选，必须命中的标签
    "preferred_tags": ["经济补偿金"]    // 可选，优先加分的标签
  }
  ```

  - **Redis 缓存**：查询结果自动缓存 5 分钟，重复查询直接返回。

### 3.7 图谱 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/knowledge/graph/search` | 搜索图谱实体 |
| POST | `/api/knowledge/graph/neighbors` | 获取实体邻居 |
| POST | `/api/knowledge/graph/path` | 查找路径 |
| POST | `/api/knowledge/graph/extract` | 从文本抽取实体 |
| POST | `/api/knowledge/graph/rag` | 图谱增强 RAG |
| POST | `/api/knowledge/graph/query` | 执行 Cypher |
| POST | `/api/knowledge/graph/reset` | 重置图谱 |

---

## 4. 与 Memory Service 的关系

- **分工**：
  - Memory Service：关注“个体 + 会话”的长期记忆，强调画像与个人偏好；
  - Knowledge Service：关注“客观知识内容”，强调领域知识与规范信息。

- **组合方式**（上游编排示例）：

  1. 每轮对话前：
     - 调用 `/api/memory/context/full` → 获得当前用户画像 + 最近对话 + 个人记忆；
     - 若用户问题与某领域有关（法律、医疗等），再调用 `/api/knowledge/...` 做知识检索；
  2. 在 LLM Prompt 中，将两侧内容分别放在不同 section：
     - 用户画像 / 个人习惯；
     - 最近对话；
     - 相关法律条文 / 专业知识片段；
  3. LLM 返回回答后，可以视情况将部分回答结果写回 Memory Service（作为新的 semantic 记忆），而知识库一般较少写回（除非有新规范发布）。

---

## 5. 写库与索引流程设计（参考 embeddingETL 项目）

原有 `embeddingETL` 项目提供了一整套 ETL 能力：

- `TextProcessor`：支持多种文件类型文本抽取（txt/pdf/docx/excel/csv/json），并做清洗 + 分块；
- `EmbeddingProcessor`：对文本块批量生成向量，支持 ZhipuAI API 或本地模型；
- `FileMonitor` + `ETLProcessor`：监控 `data_sources` 目录的新/变更文件，自动触发处理；
- `VectorDatabase`（Chroma）+ `Neo4jGraphDB`：向量存储与知识图谱写入；
- `TaskScheduler`：定时扫描、备份、清理任务。

### 5.1 新知识库索引的建议流程

短期内，可以在 Knowledge Service 之外提供一个 **独立的索引脚本/服务**，将上述 ETL 能力“改写输出目标”：

1. **输入源**：继续监控 `D:\workspace\embeddingETL\data_sources` 下的各类文件：
   - `vectors/law/*.jsonl` / `vectors/law/*.json` / 其他文本类文件；
   - `graph/law/*.csv` / `*.xlsx` / `*.json`（可选，用于写入 Neo4j）。

2. **文本抽取与分块**：
   - 直接复用 `TextProcessor.process_document` / `_process_vector_file` 的思路：
     - 支持 txt/pdf/docx/excel/csv/json/jsonl；
     - 对 JSON/JSONL 记录，透传如 `law_code/law_name/article_no/title` 等领域元数据。

3. **写入 Knowledge Service 的表**：

   对于每个“文档源文件”，流程建议：

   1. 在 `knowledge_collections` 中选定目标集合（根据 domain 决定，例如 `law`）；
   2. 在 `knowledge_documents` 中插入一条记录：
      - `external_id`（可用文件名或业务 ID）；
      - `title`（如法条标题、话术脚本名）；
      - `source_uri`（文件路径）；
      - `metadata`（文件级别的信息：例如 `{domain: 'law', law_code: '...', file_path: '...'}`）；
   3. 分块后，为每个块在 `knowledge_chunks` 中插入：
      - `document_id`、`chunk_index`、`section_label`；
      - `text`；
      - `tags`（如 `{topic: '解除劳动合同'}`）；
      - `embedding`（直接存向量数组）；
      - `importance`、`metadata`（Chunk 级元数据，如 JSONL 记录中的 `article_no/title/source` 等）。
   4. 将对应 `knowledge_documents.status` 标记为 `indexed`。

4. **领域扩展**：
   - 通过文件路径或 JSON 字段中的 `type/domain` 判断属于：`law / psychology / sales_script / medical_terms / ...`；
   - 不同领域可以映射到不同 `knowledge_collections`，但仍复用同一套表结构与索引脚本。

### 5.2 性能优化（已实现）

- **Redis 缓存**：RAG 查询结果缓存 5 分钟
- **图谱查询缓存**：搜索和邻居查询缓存 10 分钟
- **连接池**：PostgreSQL 连接池 `pool_size=10, max_overflow=20`
- **批量操作**：支持批量向量写入

---

## 6. 前端控制台与多场景应用（已实现）

前端已实现完整的知识库管理界面：

### 已实现页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 知识集合 | `/knowledge/collections` | 列表/创建集合，按 domain & project 筛选 |
| 知识文档 | `/knowledge/documents` | 文档管理，手动触发索引 |
| Knowledge RAG | `/knowledge/rag` | RAG Playground，测试检索效果 |
| 知识图谱 | `/graph` | 图谱搜索、邻居查询、可视化 |

### 后续可扩展

- 针对不同领域（法律/心理/话术/医疗）配置不同的展示视图
- Chunk 详情查看与编辑
- 批量导入工具界面

多场景可应用性来自于：

- 模型层 **领域无关**：collection/document/chunk 的抽象可以覆盖绝大多数文本类知识；
- 领域差异通过 `domain + tags + extra_metadata` 表达，而不是改表结构；
- 编排层可以自由组合 Memory Service 与 Knowledge Service 的结果，为不同业务（法律咨询、心理辅导、医疗问答、销售助理等）定制 Prompt 与策略。

---

## 7. 文本处理流水线：抽取 → 清洗 → 分块

知识库索引阶段，所有输入格式（JSONL/JSON/CSV/Excel/txt/...）最终都会经过一条统一的文本处理流水线：

1. **抽取（Extract）**

   - 目标：从各种源文件中得到「纯文本 + 结构化字段」。
   - JSONL/JSON 数组：
     - 推荐结构：一条记录 = 一条知识单元，字段中至少包含 `text`，以及 `domain/law_code/law_name/article_no/title/source/...` 等业务字段；
     - 在索引时，这些字段会被透传到 `knowledge_documents.extra_metadata` 与 `knowledge_chunks.extra_metadata` 中。
   - Excel/CSV：
     - 当前实现将每行非空单元格拼接为一行文本；
     - 后续可以约定某些列（例如 `条文号/标题/领域`）映射进 metadata。
   - 其他文本类（txt 等）：
     - 直接整文件读取为一段文本；
   - 原则：**入口可以很多样，但在“抽取结果”这一层统一成 `text + 结构化字段`。**

2. **清洗（Clean）**

   - 去除多余空白和不可见字符：`\s+ → 空格`；
   - 保留中英文、数字与常见标点，避免过度清洗损失关键符号（特别是法律条文、专业术语中的括号、编号）；
   - 合并连续标点（如 `。。。。` → `。`），减少模型噪声；
   - 核心权衡：**尽量干净，但不破坏原始语义结构**（例如条文中的序号、款项标记应保留）。

3. **分块（Chunk）**

   - 目前实现采用规则驱动的分块：
     - 递归按 `\n\n / \n / 。 / ， / 空格` 等分隔符拆分；
     - 限制每块长度不超过 `chunk_size`（默认约 512 字符）；
     - 在相邻块间加入 `chunk_overlap`（默认约 50 字符）作为上下文过渡。
   - 这样可以兼顾：
     - 文本不过长，不会轻易超出向量模型和下游 LLM 的上下文长度；
     - 语义相近的内容仍然聚合在同一块或相邻块中。

### 7.1 手动章节/段落切分的可能优化

对于某些知识类型（特别是法律条文、标准规范、长篇文档），**按章节/条号/段落手动（或半自动）切分**往往优于纯规则分块：

- 例如：
  - 以「章 / 节 / 条 / 款」为基础单位，每条法条作为一个或少数几个 chunk；
  - 对于心理学或教材类内容，以自然段或小节标题为边界；
- 优点：
  - chunk 的语义边界更清晰，更贴近人类理解方式；
  - 便于在前端展示（例如直接显示「第 X 条」的完整内容）；
  - 在图谱或结构化查询场景下，可以直接按「条文编号 / 段落编号」定位。

当前实现采用通用分块策略，后续可以在以下方向增强：

- 在源 JSONL/JSON 中直接提供「章节/条文/段落」字段，由索引程序按这些边界优先分块；
- 或对特定 domain（如 `law`）实现定制的切分策略（例如根据「第 X 条」「第一章」等模式识别边界）。

### 7.2 与前端可视化 & 图谱的关系

- **知识库可视化**：
  - 前端需要能够查看：
    - 某个文档下的 chunk 列表（`section_label + text + metadata`）；
    - 不同领域（法律/心理/话术/医疗）下 chunk 的结构差异；
  - 便于验证抽取/清洗/分块是否合理，并为后续调参提供依据。

- **图谱可视化**：
  - 对于有图谱数据源（例如 CSV/Excel/JSON 定义的节点与关系）的场景，
    - 一部分知识会进入 Neo4j（结构化图）；
    - 另一部分文本解释/条文说明会进入 Knowledge Service（chunks）.
  - 前端应当同时支持：
    - 查看图谱结构（节点/关系）及其属性；
    - 查看与图谱节点关联的文本 chunk；
  - 这样，最终在 MCP/Agent 视角下，既能看到「结构化关系」（图谱），又能看到「自然语言上下文」（知识库），共同服务于“用户一句话 → 最优上下文优化”。

## 8. 向量数据源格式建议（JSONL / JSON）

为了便于后续批量构建知识库，本节给出**推荐的向量数据源格式**。索引程序当前已支持通用 JSONL/JSON 数组读取，并会透传下述字段到 `knowledge_documents.extra_metadata` 与 `knowledge_chunks.extra_metadata` 中。

> ⚠️ **重要说明（2025-12 初始接入阶段）：**
> 
> - 当前实际接入的数据（法律条文 / 案例等）**尚未系统性建设 tags 体系**，只是在代码与格式层面预留了 `tags` 字段和基于 `required_tags` / `preferred_tags` 的轻量过滤与加权能力；
> - 在未显式写入 `tags` 的情况下，RAG 行为等价于“只按向量相似度 + importance 排序”，不会产生隐含的标签过滤；
> - **大规模 tag 设计与标注工作预计在真正做知识库工程化（按 domain 分批清洗、整理、验证）时再启动**，届时可以结合业务方需求统一规划标签体系与写库策略。

### 8.1 通用字段约定

推荐使用 **JSONL**（每行一条记录）或 **JSON 数组**（数组元素为记录），每条记录至少包含：

- `text`：
  - 必填，需向量化的原始文本内容；
- 通用元数据字段（可选）：
  - `domain`：知识领域，例如：`"law"` / `"psychology"` / `"sales_script"`；
  - `type`：记录类型，例如：`"law_article"` / `"judicial_interpretation"` / `"case"` / `"term"`；
  - `title`：标题或小节标题；
  - `source`：来源说明（网站、文件名、接口名称等）；
  - `tags`：可选标签数组，用于后续 RAG 检索时的 `required_tags` / `preferred_tags` 约束；
- 业务领域相关字段（按需扩展）：
  - 法律：`law_code` / `law_name` / `article_no`（条款号）；
  - 案例：`case_id` / `court_name` / `judge_date` / `case_type`；
  - 心理学：`topic` / `theory` / `level`；
  - 医疗：`term` / `department` / `icd_code` 等.

索引流程中，这些字段会：

- 在文档级别写入 `knowledge_documents.extra_metadata`（例如 `law_code`、`domain` 等）；
- 在片段级别写入 `knowledge_chunks.extra_metadata`，同时：
  - `article_no` / `title` 会被用来生成 `section_label`，便于前端展示；
  - `tags` 字段若存在，将作为 chunk 的候选标签（当前实现优先使用 `KnowledgeChunk.tags`，其次读取 `extra_metadata.tags`）。

### 8.2 法律条文（law_article）数据源示例

推荐将一条法律条文抽象为一条记录，示例 JSONL 行：

```jsonc
{"id": "labor_law_第二十条", "type": "law_article", "domain": "law", "law_code": "labor_law", "law_name": "中华人民共和国劳动法", "article_no": "第二十条", "title": "劳动合同的期限", "tags": ["劳动合同", "期限"], "text": "劳动合同的期限分为有固定期限、无固定期限和以完成一定的工作为期限。..."}
```

索引后效果：

- `section_label` ≈ `"第二十条"`；
- `extra_metadata` 中可直接看到 `law_code` / `law_name` / `article_no` / `title` 等；
- 若提供了 `tags`，后续 RAG 检索时可以通过 `required_tags` / `preferred_tags` 精细控制召回范围与排序.

### 8.3 司法解释 / 规范性文件示例

司法解释可以与法律条文共用 `law_article` 结构，只需在 `type` 或 `law_code` 中区分来源：

```jsonc
{"id": "spc_interpretation_劳动争议_第一条", "type": "judicial_interpretation", "domain": "law", "law_code": "spc_interpretation_labor_dispute", "law_name": "最高人民法院关于审理劳动争议案件适用法律若干问题的解释", "article_no": "第一条", "title": "受案范围", "tags": ["劳动争议", "受案范围"], "text": "人民法院受理下列因执行劳动合同发生的劳动争议案件：..."}
```

后续在 RAG 检索或上游编排时，可以：

- 根据 `type = "judicial_interpretation"` 或 `law_code` 过滤司法解释；
- 在排序时对不同 `type` 赋予不同权重（例如法律条文与司法解释权重略高于案例和评论）。

### 8.4 案例（case）数据源示例

对于裁判文书 / 指导性案例，可以将每个「要旨 / 裁判要点 / 事实+理由」作为独立记录：

```jsonc
{"id": "guiding_case_劳动合同_001", "type": "case", "domain": "law", "case_id": "(2023)最高法民申123号", "law_code": "labor_law", "title": "劳动合同解除中的证据责任分配", "court_name": "最高人民法院", "judge_date": "2023-05-20", "tags": ["劳动合同", "解除", "证据责任"], "text": "本案中，用人单位主张劳动者严重违反规章制度，应当对相关事实承担举证责任。..."}
```

这样可以在检索层面：

- 通过 `case_id` / `court_name` / `judge_date` 在前端展示更多上下文；
- 根据 `tags` 与 `law_code` 将案例与对应法律条文关联起来（后续若接入图谱，可在图结构中显式建立“案例 → 法条”边）。

### 8.5 兼容性说明

- 索引实现对字段是**宽松读取**的：
  - 只要包含 `text` 字段即可被索引；
  - 其余字段若存在，会自动透传为 `extra_metadata`，并在必要时用于 `section_label`、tags 等；
- 因此：
  - 可以从最小结构 `{"text": "..."}` 起步；
  - 随着项目迭代逐步丰富 `domain/type/law_code/article_no/tags/...`，无需修改索引代码.

> 本文档仅作为知识库子系统的设计与当前实现说明。后续随着索引/RAG API 与前端管理页面完善，可以继续在本文件中补充“接口调用示例”、“典型业务场景 Flow”、“与 Neo4j 图谱结合方式”等章节.
