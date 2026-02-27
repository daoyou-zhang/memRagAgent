# memRagAgent - 智能认知记忆系统

> 一个基于记忆增强检索（Memory-Augmented RAG）的智能对话系统，具备自我学习与进化能力

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19.2-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104-009688.svg)](https://fastapi.tiangolo.com/)

## 项目简介

memRagAgent 是一个创新的智能对话系统，通过记忆增强检索（Memory-Augmented RAG）技术，实现了具备长期记忆、自我学习和工具调用能力的 AI 助手。系统采用微服务架构，将认知、记忆和知识管理分离，构建了一个可扩展的智能体框架。

### 核心特性

- **记忆增强检索（Memory RAG）**：结合情节记忆、语义记忆和程序记忆的三层记忆系统
- **自我学习与进化**：从对话中自动提取知识洞察，持续优化认知能力
- **MCP 工具系统**：支持动态工具注册与编排，可扩展外部能力
- **知识图谱集成**：Neo4j 驱动的知识图谱，支持复杂关系推理
- **多租户架构**：完整的租户隔离与 API Key 认证机制
- **流式对话**：支持实时流式输出，提升用户体验

## 技术架构

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
│  FastAPI :8000    │──│  Flask :5000 │  │   Flask :5001     │
│  认知/意图/MCP    │  │  记忆/RAG    │  │   知识库/图谱     │
└───────────────────┘  └──────────────┘  └───────────────────┘
```

### 技术栈

**前端**
- React 19 + TypeScript
- Vite 7 构建工具
- React Router 7 路由管理
- Vis.js 图谱可视化

**后端**
- FastAPI (认知服务)
- Flask (记忆服务 + 知识服务)
- PostgreSQL (结构化数据)
- Neo4j (知识图谱)
- Redis (缓存层)

**AI 能力**
- 通义千问 / DeepSeek / 智谱 AI
- 支持 OpenAI 兼容 API
- 向量检索与语义匹配

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Neo4j 5.x
- Redis 7.x

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/daoyou-zhang/memRagAgent.git
cd memRagAgent
```

2. **后端配置**
```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库和 API Key 配置
```

3. **前端配置**
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

4. **启动服务**
```bash
# 在 backend 目录下
python start_all.py
```

服务将在以下端口启动：
- 前端：http://localhost:5173
- 认知服务：http://localhost:8000
- 记忆服务：http://localhost:5000
- 知识服务：http://localhost:5001

### 配置说明

**backend/daoyou_agent/.env**
```env
# 主模型（回复生成）
MODEL_NAME=deepseek-v3.2-exp
API_MODEL_KEYS=sk-your-api-key
API_MODEL_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# 意图模型（可选）
INTENT_MODEL_NAME=qwen-flash
INTENT_API_KEYS=sk-your-api-key

# 记忆服务地址
MEMORY_SERVICE_BASE_URL=http://127.0.0.1:5000
```

## 核心功能

### 1. 认知对话系统

基于意图理解 → 上下文聚合 → 回复生成 → 学习闭环的完整认知流程：

```python
# 认知处理流程
用户输入 → 意图分析 → 上下文检索 → LLM 生成 → 记忆存储 → 画像更新
```

### 2. 三层记忆系统

| 记忆类型 | 说明 | 示例 |
|---------|------|------|
| Episodic | 情节记忆，记录具体对话 | "用户在 2024-01-01 询问了天气" |
| Semantic | 语义记忆，提炼知识概念 | "用户喜欢户外运动" |
| Procedural | 程序记忆，记录操作步骤 | "查询天气的 API 调用流程" |

### 3. MCP 工具系统

支持动态工具注册与编排，内置工具包括：

- **八字排盘**：传统命理计算
- **文件读取**：代码审查与分析
- **知识检索**：知识库查询
- 更多工具持续扩展中...

### 4. 知识图谱

基于 Neo4j 的知识图谱系统，支持：
- 实体关系建模
- 图谱可视化
- 路径查询与推理
- 社区发现

## 项目结构

```
memRagAgent/
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── api/             # API 客户端
│   │   ├── components/      # 可复用组件
│   │   ├── pages/           # 页面组件
│   │   └── App.tsx          # 主应用
│   └── package.json
│
├── backend/
│   ├── daoyou_agent/        # 认知服务 (FastAPI)
│   │   ├── api/             # API 路由
│   │   ├── services/        # 核心服务
│   │   ├── models/          # 数据模型
│   │   ├── tools/           # MCP 工具
│   │   └── app.py           # 应用入口
│   │
│   ├── memory/              # 记忆服务 (Flask)
│   │   ├── routes/          # API 路由
│   │   ├── services/        # 记忆管理
│   │   └── app.py
│   │
│   ├── knowledge/           # 知识服务 (Flask)
│   │   ├── routes/          # API 路由
│   │   ├── services/        # 知识管理
│   │   └── app.py
│   │
│   └── requirements.txt     # Python 依赖
│
└── README.md                # 本文档
```

## API 文档

### 认知 API

**POST /api/v1/cognitive/process**

处理用户输入，返回智能回复

```json
{
  "input": "你好，今天天气怎么样？",
  "user_id": "user123",
  "session_id": "session456",
  "project_id": "project789"
}
```

### 记忆 API

- `POST /api/memory/memories` - 创建记忆
- `GET /api/memory/memories` - 查询记忆
- `POST /api/memory/context/full` - 获取完整上下文
- `POST /api/memory/jobs/profile/auto` - 触发画像聚合

### 知识 API

- `POST /api/knowledge/collections` - 创建知识集合
- `POST /api/knowledge/documents` - 上传文档
- `POST /api/knowledge/rag` - 知识检索
- `GET /api/knowledge/graph/search` - 图谱搜索

完整 API 文档请访问：
- 认知服务：http://localhost:8000/docs
- 记忆服务：http://localhost:5000/docs
- 知识服务：http://localhost:5001/docs

## 开发路线图

- [x] 三层记忆系统
- [x] 认知对话引擎
- [x] MCP 工具框架
- [x] 知识图谱集成
- [x] 多租户架构
- [x] 自我学习机制
- [ ] WebSocket 流式输出
- [ ] 多模型协作
- [ ] 代码执行沙箱
- [ ] Docker 一键部署
- [ ] 移动端适配

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- 项目地址：https://github.com/daoyou-zhang/memRagAgent
- 问题反馈：https://github.com/daoyou-zhang/memRagAgent/issues

## 致谢

感谢以下开源项目的支持：
- FastAPI / Flask
- React / Vite
- PostgreSQL / Neo4j
- 通义千问 / DeepSeek

---

⭐ 如果这个项目对你有帮助，欢迎 Star 支持！
