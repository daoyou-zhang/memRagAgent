# memRagAgent - Intelligent Cognitive Memory System

> An intelligent dialogue system based on Memory-Augmented RAG technology with self-learning and evolution capabilities

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19.2-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104-009688.svg)](https://fastapi.tiangolo.com/)

[中文文档](README.md) | English

## Overview

memRagAgent is an innovative intelligent dialogue system that implements an AI assistant with long-term memory, self-learning, and tool invocation capabilities through Memory-Augmented RAG technology. The system adopts a microservices architecture, separating cognition, memory, and knowledge management to build a scalable intelligent agent framework.

### Core Features

- **Memory-Augmented RAG**: Three-layer memory system combining episodic, semantic, and procedural memory
- **Self-Learning & Evolution**: Automatically extracts knowledge insights from conversations to continuously optimize cognitive quality
- **MCP Tool System**: Supports dynamic tool registration and orchestration for extensible capabilities
- **Knowledge Graph Integration**: Neo4j-powered knowledge graph supporting complex relationship reasoning
- **Multi-Tenant Architecture**: Complete tenant isolation with API Key authentication
- **Streaming Conversations**: Real-time streaming output for enhanced user experience

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (React + Vite)                    │
│                    localhost:5173                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Cognitive      │  │  Memory      │  │  Knowledge    │  │
│  │  Console        │  │  Console     │  │  Management   │  │
│  └────────┬────────┘  └──────┬───────┘  └───────┬───────┘  │
│           │                  │                   │          │
└───────────┼──────────────────┼───────────────────┼──────────┘
            │                  │                   │
            ▼                  ▼                   ▼
┌───────────────────┐  ┌──────────────┐  ┌───────────────────┐
│  daoyou_agent     │  │   memory     │  │    knowledge      │
│  FastAPI :8000    │──│  Flask :5000 │  │   Flask :5001     │
│  Cognition/MCP    │  │  Memory/RAG  │  │   KB/Graph        │
└───────────────────┘  └──────────────┘  └───────────────────┘
```

### Tech Stack

**Frontend**
- React 19 + TypeScript
- Vite 7 Build Tool
- React Router 7
- Vis.js for Graph Visualization

**Backend**
- FastAPI (Cognitive Service)
- Flask (Memory + Knowledge Services)
- PostgreSQL (Structured Data)
- Neo4j (Knowledge Graph)
- Redis (Cache Layer)

**AI Capabilities**
- Qwen / DeepSeek / Zhipu AI
- OpenAI-Compatible API Support
- Vector Retrieval & Semantic Matching

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Neo4j 5.x
- Redis 7.x

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/daoyou-zhang/memRagAgent.git
cd memRagAgent
```

2. **Backend Setup**
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database and API key configurations
```

3. **Frontend Setup**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

4. **Start Services**
```bash
# In backend directory
python start_all.py
```

Services will start on:
- Frontend: http://localhost:5173
- Cognitive Service: http://localhost:8000
- Memory Service: http://localhost:5000
- Knowledge Service: http://localhost:5001

### Configuration

**backend/daoyou_agent/.env**
```env
# Main Model (Response Generation)
MODEL_NAME=deepseek-v3.2-exp
API_MODEL_KEYS=sk-your-api-key
API_MODEL_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# Intent Model (Optional)
INTENT_MODEL_NAME=qwen-flash
INTENT_API_KEYS=sk-your-api-key

# Memory Service URL
MEMORY_SERVICE_BASE_URL=http://127.0.0.1:5000
```

## Core Features

### 1. Cognitive Dialogue System

Complete cognitive flow based on: Intent Analysis → Context Aggregation → Response Generation → Learning Loop

```python
# Cognitive Processing Flow
User Input → Intent Analysis → Context Retrieval → LLM Generation → Memory Storage → Profile Update
```

### 2. Three-Layer Memory System

| Memory Type | Description | Example |
|------------|-------------|---------|
| Episodic | Records specific conversations | "User asked about weather on 2024-01-01" |
| Semantic | Extracts knowledge concepts | "User enjoys outdoor activities" |
| Procedural | Stores operation procedures | "Weather API call workflow" |

### 3. MCP Tool System

Supports dynamic tool registration and orchestration. Built-in tools include:

- **BaZi Calculator**: Traditional Chinese astrology
- **File Reader**: Code review and analysis
- **Knowledge Search**: Knowledge base queries
- More tools continuously expanding...

### 4. Knowledge Graph

Neo4j-based knowledge graph system supporting:
- Entity-Relationship Modeling
- Graph Visualization
- Path Queries & Reasoning
- Community Detection

## Project Structure

```
memRagAgent/
├── frontend/                 # React Frontend
│   ├── src/
│   │   ├── api/             # API Clients
│   │   ├── components/      # Reusable Components
│   │   ├── pages/           # Page Components
│   │   └── App.tsx          # Main Application
│   └── package.json
│
├── backend/
│   ├── daoyou_agent/        # Cognitive Service (FastAPI)
│   │   ├── api/             # API Routes
│   │   ├── services/        # Core Services
│   │   ├── models/          # Data Models
│   │   ├── tools/           # MCP Tools
│   │   └── app.py           # Application Entry
│   │
│   ├── memory/              # Memory Service (Flask)
│   │   ├── routes/          # API Routes
│   │   ├── services/        # Memory Management
│   │   └── app.py
│   │
│   ├── knowledge/           # Knowledge Service (Flask)
│   │   ├── routes/          # API Routes
│   │   ├── services/        # Knowledge Management
│   │   └── app.py
│   │
│   └── requirements.txt     # Python Dependencies
│
└── README.md                # This Document
```

## API Documentation

### Cognitive API

**POST /api/v1/cognitive/process**

Process user input and return intelligent response

```json
{
  "input": "Hello, how's the weather today?",
  "user_id": "user123",
  "session_id": "session456",
  "project_id": "project789"
}
```

### Memory API

- `POST /api/memory/memories` - Create memory
- `GET /api/memory/memories` - Query memories
- `POST /api/memory/context/full` - Get full context
- `POST /api/memory/jobs/profile/auto` - Trigger profile aggregation

### Knowledge API

- `POST /api/knowledge/collections` - Create knowledge collection
- `POST /api/knowledge/documents` - Upload document
- `POST /api/knowledge/rag` - Knowledge retrieval
- `GET /api/knowledge/graph/search` - Graph search

Complete API documentation available at:
- Cognitive Service: http://localhost:8000/docs
- Memory Service: http://localhost:5000/docs
- Knowledge Service: http://localhost:5001/docs

## Roadmap

- [x] Three-layer memory system
- [x] Cognitive dialogue engine
- [x] MCP tool framework
- [x] Knowledge graph integration
- [x] Multi-tenant architecture
- [x] Self-learning mechanism
- [ ] WebSocket streaming output
- [ ] Multi-model collaboration
- [ ] Code execution sandbox
- [ ] Docker one-click deployment
- [ ] Mobile adaptation

## Contributing

Issues and Pull Requests are welcome!

1. Fork this repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details

## Contact

- Project URL: https://github.com/daoyou-zhang/memRagAgent
- Issue Tracker: https://github.com/daoyou-zhang/memRagAgent/issues

## Acknowledgments

Thanks to the following open source projects:
- FastAPI / Flask
- React / Vite
- PostgreSQL / Neo4j
- Qwen / DeepSeek

---

⭐ If this project helps you, please give it a Star!
