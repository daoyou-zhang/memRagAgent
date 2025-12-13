# memRagAgent - Knowledge 服务

知识库管理服务，负责知识存储、索引、RAG 检索和图谱增强。

## 架构定位

```
┌─────────────────────────────────────────────────────────────┐
│                    daoyou_agent (编排层)                     │
│        意图理解 → 上下文聚合 → 回复生成                       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │ Memory  │     │Knowledge│     │  Neo4j  │
        │  :5000  │     │  :5001  │     │  图谱   │
        └─────────┘     └─────────┘     └─────────┘
```

## 核心功能

### 1. 知识集合 (Collection)
按领域组织知识：
- `law` - 法律法规
- `psychology` - 心理学
- `sales_script` - 销售话术
- `medical_terms` - 医疗术语

### 2. 文档管理 (Document)
- 支持格式: txt/pdf/docx/json/jsonl
- 状态流转: raw → parsed → indexed

### 3. 知识分块 (Chunk)
- 智能分块（按段落/章节）
- 向量嵌入存储
- 元数据标签

### 4. 知识图谱
- Neo4j 实体关系存储
- 图谱增强 RAG
- 多跳推理支持

## API 接口

### 集合管理 `/api/knowledge`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/collections` | 创建集合 |
| GET | `/collections` | 列出集合 |
| GET | `/collections/:id` | 集合详情 |
| DELETE | `/collections/:id` | 删除集合 |

### 文档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/documents` | 创建文档 |
| GET | `/documents` | 列出文档 |
| POST | `/documents/:id/index` | 索引文档 |
| GET | `/documents/:id/chunks` | 获取分块 |
| DELETE | `/documents/:id` | 删除文档 |

### RAG 检索

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/rag/query` | 知识库 RAG |
| POST | `/rag/hybrid` | 混合检索（向量+图谱） |

### 图谱操作 `/api/graph`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/search` | 图谱搜索 |
| POST | `/query` | 执行 Cypher |
| GET | `/entity/:name` | 获取实体 |
| GET | `/neighbors/:name` | 获取邻居 |
| POST | `/rag` | 图谱增强 RAG |
| POST | `/reset` | 重置图谱 |

## 图谱增强 RAG

```
用户查询
    │
    ▼
┌──────────────────────────────────────┐
│  1. 提取关键词/实体                   │
│  2. 图谱搜索相关节点                  │
│  3. 扩展邻居节点                     │
│  4. 格式化图谱上下文                  │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│  向量检索 + 图谱上下文 → LLM 生成     │
└──────────────────────────────────────┘
```

## 数据库表

```sql
-- 知识集合
knowledge_collections (
    id, project_id, name, domain, description, ...
)

-- 知识文档
knowledge_documents (
    id, collection_id, external_id, title, source_uri, status, ...
)

-- 知识分块
knowledge_chunks (
    id, document_id, chunk_index, section_label, text, embedding, ...
)
```

## 环境变量

```bash
# 数据库
POSTGRES_HOST=localhost
POSTGRES_DB=memrag

# Neo4j 图谱
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DB=neo4j

# Embedding
EMBEDDINGS_NAME=embedding-3
API_EMBEDDINGS_KEY=xxx
API_EMBEDDINGS_BASE=https://api.example.com/v4

# LLM (用于实体抽取)
MODEL_NAME=qwen-plus
API_MODEL_KEYS=sk-xxx
API_MODEL_BASE=https://api.example.com/v1
```

## 启动服务

```bash
cd backend/knowledge
python app.py
# 服务运行在 http://localhost:5001
```

## 开发路线

- [x] 集合/文档/分块 CRUD
- [x] 文档索引（分块+向量）
- [x] 知识库 RAG
- [x] Neo4j 图谱集成
- [x] 图谱搜索
- [x] 图谱增强 RAG
- [x] LLM 实体抽取
- [ ] 批量导入工具
- [ ] 增量更新索引
