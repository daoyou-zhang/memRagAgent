# memRagAgent 测试指南

## 快速开始

### 1. 启动服务

```bash
# 终端 1: Memory 服务
cd backend/memory && python app.py

# 终端 2: Knowledge 服务
cd backend/knowledge && python app.py

# 终端 3: Agent 服务
cd backend/daoyou_agent && python app.py

# 终端 4: 前端
cd frontend && npm run dev
```

### 2. 运行自动化测试

```bash
cd backend

# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行所有测试
pytest tests/ -v

# 运行单个模块
pytest tests/test_memory_api.py -v
pytest tests/test_knowledge_api.py -v
pytest tests/test_agent_api.py -v
pytest tests/test_integration.py -v

# 只运行快速测试（跳过慢速测试）
pytest tests/ -v -m "not slow"

# 生成测试报告
pytest tests/ -v --html=test_report.html
```

---

## 手动测试清单

### Memory 服务 (端口 5000)

#### 健康检查
```bash
curl http://127.0.0.1:5000/health
# 期望: {"status": "healthy"}
```

#### 创建记忆
```bash
curl -X POST http://127.0.0.1:5000/api/memory/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "project_id": "p1",
    "type": "episodic",
    "content": "今天天气很好，我去公园散步了",
    "importance": 0.7
  }'
```

#### 查询记忆
```bash
curl "http://127.0.0.1:5000/api/memory/memories?user_id=test_user&limit=10"
```

#### RAG 检索
```bash
curl -X POST http://127.0.0.1:5000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "query": "天气",
    "top_k": 5
  }'
```

#### 获取用户画像
```bash
curl http://127.0.0.1:5000/api/profiles/test_user
```

#### 完整上下文
```bash
curl -X POST http://127.0.0.1:5000/api/memory/context/full \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "query": "我最近做了什么",
    "memory_depth": 10
  }'
```

#### 租户管理
```bash
# 列出租户
curl http://127.0.0.1:5000/api/tenants

# 创建租户
curl -X POST http://127.0.0.1:5000/api/tenants \
  -H "Content-Type: application/json" \
  -d '{"code": "test_tenant", "name": "测试租户", "type": "personal"}'
```

---

### Knowledge 服务 (端口 5001)

#### 健康检查
```bash
curl http://127.0.0.1:5001/health
```

#### 知识集合
```bash
# 列出集合
curl http://127.0.0.1:5001/api/knowledge/collections

# 创建集合
curl -X POST http://127.0.0.1:5001/api/knowledge/collections \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "p1",
    "name": "法律知识库",
    "domain": "legal",
    "description": "法律法规文档集合"
  }'
```

#### 知识文档
```bash
# 列出文档
curl http://127.0.0.1:5001/api/knowledge/documents

# 创建文档（需要 collection_id）
curl -X POST http://127.0.0.1:5001/api/knowledge/documents \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": 1,
    "title": "合同法概述",
    "content": "合同是平等主体之间设立、变更、终止民事权利义务关系的协议...",
    "source_type": "manual"
  }'
```

#### 知识库 RAG
```bash
curl -X POST http://127.0.0.1:5001/api/knowledge/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "合同违约责任",
    "domain": "legal",
    "top_k": 5
  }'
```

#### 图谱搜索
```bash
curl "http://127.0.0.1:5001/api/knowledge/graph/search?query=合同&limit=10"
```

---

### Agent 服务 (端口 8000)

#### 健康检查
```bash
curl http://127.0.0.1:8000/health
```

#### 认知对话（非流式）
```bash
curl -X POST http://127.0.0.1:8000/api/v1/cognitive/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "你好，请介绍一下你自己",
    "user_id": "test_user",
    "session_id": "s1",
    "stream": false
  }'
```

#### 认知对话（带记忆）
```bash
curl -X POST http://127.0.0.1:8000/api/v1/cognitive/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "我之前跟你说过什么？",
    "user_id": "test_user",
    "session_id": "s1",
    "use_memory": true,
    "memory_depth": 10,
    "stream": false
  }'
```

#### 认知对话（八字排盘）
```bash
curl -X POST http://127.0.0.1:8000/api/v1/cognitive/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "帮我排一下八字，1990年5月15日上午10点出生",
    "user_id": "test_user",
    "stream": false
  }'
```

#### 工具列表
```bash
curl http://127.0.0.1:8000/api/v1/tools
```

#### Prompt 管理
```bash
# 获取默认 Prompt
curl http://127.0.0.1:8000/api/v1/prompts/default

# 获取行业列表
curl http://127.0.0.1:8000/api/v1/prompts/industries

# 获取模板
curl http://127.0.0.1:8000/api/v1/prompts/templates

# 创建自定义配置
curl -X POST http://127.0.0.1:8000/api/v1/prompts/configs \
  -H "Content-Type: application/json" \
  -d '{
    "category": "custom_test",
    "name": "自定义测试配置",
    "response_system_prompt": "你是一个测试助手。"
  }'

# 获取配置列表
curl http://127.0.0.1:8000/api/v1/prompts/configs
```

---

## 前端页面测试清单

| # | 页面 | 路径 | 测试内容 |
|---|------|------|----------|
| 1 | 首页 | `/` | 加载正常，导航可用 |
| 2 | 认知对话 | `/cognitive` | 发送消息、收到回复、意图分析显示 |
| 3 | 创建记忆 | `/memories/create` | 表单提交、成功提示 |
| 4 | 查询记忆 | `/memories/query` | 搜索功能、结果显示 |
| 5 | 记忆清理 | `/memories/cleanup` | 批量选择、删除确认 |
| 6 | 生成任务 | `/jobs` | 任务列表、状态显示 |
| 7 | 用户画像 | `/profiles` | 画像加载、结构化显示 |
| 8 | Memory RAG | `/rag` | 查询功能、相似度显示 |
| 9 | Full Context | `/full-context` | 上下文聚合显示 |
| 10 | 知识集合 | `/knowledge/collections` | CRUD 操作 |
| 11 | 知识文档 | `/knowledge/documents` | 文档管理 |
| 12 | Knowledge RAG | `/knowledge/rag` | 知识库检索 |
| 13 | 知识图谱 | `/graph` | 图谱可视化（需 Neo4j） |
| 14 | 多租户管理 | `/tenants` | 租户/用户组/用户管理 |
| 15 | 系统状态 | `/system` | 服务健康检查 |

---

## 常见问题排查

### 服务无法启动

```bash
# 检查端口占用
netstat -ano | findstr :5000
netstat -ano | findstr :5001
netstat -ano | findstr :8000

# 检查数据库连接
psql -d memrag -c "SELECT 1"

# 检查 Redis
redis-cli ping
```

### API 返回 500

```bash
# 查看服务日志
# Memory 服务日志在终端输出
# 检查数据库表是否存在
psql -d memrag -c "\dt"
```

### 前端无法连接后端

```bash
# 检查 CORS
# 确保后端启用了 CORS

# 检查代理配置（vite.config.ts）
```

---

## 测试数据清理

```sql
-- 清理测试数据
DELETE FROM memories WHERE user_id LIKE 'test_%';
DELETE FROM profiles WHERE user_id LIKE 'test_%';
DELETE FROM conversation_sessions WHERE user_id LIKE 'test_%';
DELETE FROM prompt_configs WHERE category LIKE 'test_%';
```
