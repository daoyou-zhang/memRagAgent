# memRagAgent - Frontend

基于 React + TypeScript + Vite 的现代化管理界面。

## 技术栈

- **框架**: React 18 + TypeScript
- **构建**: Vite 6
- **路由**: React Router 7
- **样式**: CSS Variables (深色主题)
- **HTTP**: Fetch API

## 功能页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 首页 | `/` | 系统概览 |
| 认知对话 | `/cognitive` | AI 对话界面（流式） |
| 创建记忆 | `/memories/create` | 手动创建记忆 |
| 查询记忆 | `/memories/query` | 搜索和浏览记忆 |
| 记忆清理 | `/memories/cleanup` | 批量删除记忆 |
| 生成任务 | `/jobs` | 任务创建和执行 |
| 用户画像 | `/profiles` | 画像查看和刷新 |
| Memory RAG | `/rag` | 记忆 RAG 测试 |
| Full Context | `/full-context` | 完整上下文测试 |
| 知识集合 | `/knowledge/collections` | 集合管理 |
| 知识文档 | `/knowledge/documents` | 文档管理和索引 |
| Knowledge RAG | `/knowledge/rag` | 知识库 RAG 测试 |
| 知识图谱 | `/graph` | 图谱可视化和搜索 |
| 多租户管理 | `/tenants` | 租户/用户/API Key 管理 |
| 设置 | `/settings` | API Key 和 Project ID 配置 |
| 系统状态 | `/system` | 服务状态监控和功能测试 |

## 项目结构

```
frontend/
├── src/
│   ├── api/                 # API 客户端
│   │   ├── http.ts          # HTTP 封装 + 认证
│   │   ├── cognitive.ts     # 认知对话 API
│   │   ├── memory.ts        # 记忆 API
│   │   ├── knowledge.ts     # 知识库 API
│   │   ├── jobs.ts          # 任务 API
│   │   ├── profiles.ts      # 画像 API
│   │   └── rag.ts           # RAG API
│   │
│   ├── components/          # 可复用组件
│   │   └── MemoizedList.tsx # Memoized 列表组件
│   │
│   ├── pages/               # 页面组件
│   │   ├── CognitivePage.tsx
│   │   ├── MemoryQueryPage.tsx
│   │   ├── KnowledgeDocumentsPage.tsx
│   │   ├── GraphPage.tsx
│   │   └── ...
│   │
│   ├── App.tsx              # 主应用（路由+侧边栏）
│   └── App.css              # 全局样式（深色主题）
│
├── index.html
├── vite.config.ts
└── package.json
```

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式
npm run dev
# 访问 http://localhost:5173

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

## 配置

### API 地址

编辑 `src/api/http.ts` 修改后端地址：

```typescript
const BASE_URLS = {
  memory: 'http://localhost:5000',
  knowledge: 'http://localhost:5001',
  agent: 'http://localhost:8000',
}
```

### 认证配置

前端通过 HTTP 客户端自动附加认证头：

```typescript
// src/api/http.ts
import { getApiKey, getProjectId } from './http'

// 自动附加到所有请求
headers['X-API-Key'] = getApiKey()
headers['X-Project-Id'] = getProjectId()
```

**设置方式：**

1. 访问 `/tenants` 页面创建租户和 API Key
2. 访问 `/settings` 页面配置 API Key 和 Project ID
3. 或通过浏览器控制台手动设置：

```javascript
localStorage.setItem('memrag_api_key', 'sk-xxx')
localStorage.setItem('memrag_project_id', 'DAOYOUTEST')
```

详细认证机制参见 [TENANT_SECURITY.md](../TENANT_SECURITY.md)。

## 设计特点

### 深色主题
- CSS Variables 定义颜色系统
- 护眼的深色背景
- 高对比度文字

### 侧边栏导航
- 分组菜单（对话/记忆/检索/知识库）
- 当前页面高亮
- 响应式布局

### 性能优化
- React.memo 优化列表渲染
- 组件级代码分割
- 按需加载

## 开发路线

- [x] 深色主题 UI
- [x] 侧边栏导航
- [x] 认知对话（流式）
- [x] 记忆管理页面
- [x] 知识库管理页面
- [x] 图谱可视化
- [x] React.memo 优化
- [x] API Key 认证
- [x] 多租户管理页面
- [x] 用户/API Key 管理
- [ ] 错误边界
- [ ] 移动端适配
