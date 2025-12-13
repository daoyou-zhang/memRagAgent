import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import './App.css'
import HomePage from './pages/HomePage'
import MemoryCreatePage from './pages/MemoryCreatePage'
import MemoryQueryPage from './pages/MemoryQueryPage'
import MemoryCleanupPage from './pages/MemoryCleanupPage'
import RagPage from './pages/RagPage'
import ProfilesPage from './pages/ProfilesPage'
import JobsPage from './pages/JobsPage'
import FullContextPage from './pages/FullContextPage'
import KnowledgeCollectionsPage from './pages/KnowledgeCollectionsPage'
import KnowledgeDocumentsPage from './pages/KnowledgeDocumentsPage'
import KnowledgeRagPage from './pages/KnowledgeRagPage'
import GraphPage from './pages/GraphPage'
import CognitivePage from './pages/CognitivePage'

function AppShell() {
  const location = useLocation()

  return (
    <div className="App" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.75rem 1.5rem',
          borderBottom: '1px solid #ddd',
        }}
      >
        <div>
          <span style={{ fontWeight: 'bold' }}>memRagAgent Console</span>
        </div>
        {location.pathname !== '/' && (
          <nav className="app-nav" style={{ display: 'flex', gap: '1rem' }}>
            {/* 首页入口：记忆管理 / 知识库均可返回 */}
            <Link to="/">首页</Link>

            {/* 道友认知测试台 */}
            {location.pathname.startsWith('/cognitive') && (
              <>
                <Link to="/cognitive">认知测试台</Link>
                <a href="http://localhost:8000/test/stream" target="_blank" rel="noopener noreferrer">流式响应测试</a>
              </>
            )}

            {/* 记忆管理相关路由时展示的导航 */}
            {(
              location.pathname.startsWith('/memories') ||
              location.pathname.startsWith('/jobs') ||
              location.pathname.startsWith('/rag') ||
              location.pathname.startsWith('/profiles') ||
              location.pathname.startsWith('/full-context')
            ) && (
              <>
                <Link to="/memories/create">创建记忆</Link>
                <Link to="/memories/query">查询记忆</Link>
                <Link to="/memories/cleanup">记忆清理</Link>
                <Link to="/jobs">记忆生成 Job</Link>
                <Link to="/rag">RAG 检索实验台</Link>
                <Link to="/profiles">画像查看</Link>
                <Link to="/full-context">Full Context 实验台</Link>
              </>
            )}

            {/* 知识库 / 图谱相关路由时展示的导航 */}
            {(location.pathname.startsWith('/knowledge') || location.pathname.startsWith('/graph')) && (
              <>
                <Link to="/knowledge/collections">知识集合</Link>
                <Link to="/knowledge/documents">知识文档</Link>
                <Link to="/knowledge/rag">知识库 RAG</Link>
                <Link to="/graph">知识图谱</Link>
              </>
            )}
          </nav>
        )}
      </header>

      <main style={{ flex: 1, padding: '1rem' }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/memories/create" element={<MemoryCreatePage />} />
          <Route path="/memories/query" element={<MemoryQueryPage />} />
          <Route path="/memories/cleanup" element={<MemoryCleanupPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/rag" element={<RagPage />} />
          <Route path="/profiles" element={<ProfilesPage />} />
          <Route path="/full-context" element={<FullContextPage />} />
          <Route path="/knowledge" element={<KnowledgeCollectionsPage />} />
          <Route path="/knowledge/collections" element={<KnowledgeCollectionsPage />} />
          <Route path="/knowledge/documents" element={<KnowledgeDocumentsPage />} />
          <Route path="/knowledge/rag" element={<KnowledgeRagPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/cognitive" element={<CognitivePage />} />
          <Route path="*" element={<div>Not Found</div>} />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}

export default App