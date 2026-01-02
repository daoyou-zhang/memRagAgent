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
import TenantsPage from './pages/TenantsPage'
import SystemStatusPage from './pages/SystemStatusPage'
import SettingsPage from './pages/SettingsPage'
import StreamTestPage from './pages/StreamTestPage'

// 导航配置
const navGroups = [
  {
    title: '对话',
    items: [
      { path: '/cognitive', label: '认知对话', icon: '💬' },
      { path: '/digital-person', label: '3D 数字人', icon: '👩' },
    ]
  },
  {
    title: '记忆管理',
    items: [
      { path: '/memories/create', label: '创建记忆', icon: '➕' },
      { path: '/memories/query', label: '查询记忆', icon: '🔍' },
      { path: '/memories/cleanup', label: '记忆清理', icon: '🗑️' },
      { path: '/jobs', label: '生成任务', icon: '⚙️' },
      { path: '/profiles', label: '用户画像', icon: '👤' },
    ]
  },
  {
    title: '检索测试',
    items: [
      { path: '/rag', label: 'Memory RAG', icon: '🧠' },
      { path: '/full-context', label: 'Full Context', icon: '📋' },
      { path: '/knowledge/rag', label: 'Knowledge RAG', icon: '📚' },
    ]
  },
  {
    title: '知识库',
    items: [
      { path: '/knowledge/collections', label: '知识集合', icon: '📁' },
      { path: '/knowledge/documents', label: '知识文档', icon: '📄' },
      { path: '/graph', label: '知识图谱', icon: '🕸️' },
    ]
  },
  {
    title: '系统管理',
    items: [
      { path: '/tenants', label: '多租户管理', icon: '🏢' },
      { path: '/system', label: '系统状态', icon: '📊' },
      { path: '/settings', label: '设置', icon: '⚙️' },
    ]
  },
]

// 侧边栏组件
function Sidebar() {
  const location = useLocation()
  
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Link to="/" className="sidebar-logo">
          <div className="sidebar-logo-icon">🧠</div>
          <span>memRagAgent</span>
        </Link>
      </div>
      
      <nav style={{ flex: 1, overflowY: 'auto' }}>
        {navGroups.map((group, gi) => (
          <div className="nav-group" key={gi}>
            <div className="nav-group-title">{group.title}</div>
            {group.items.map((item, ii) => (
              <Link
                key={ii}
                to={item.path}
                className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
              >
                <span className="nav-item-icon">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>
      
      <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid var(--border-color)' }}>
        <Link
          to="/stream-test"
          className="nav-item"
          style={{ margin: '-0.625rem -1.25rem' }}
        >
          <span className="nav-item-icon">🔗</span>
          <span>流式测试</span>
        </Link>
      </div>
    </aside>
  )
}

// 页面标题映射
const pageTitles: Record<string, string> = {
  '/': '首页',
  '/cognitive': '认知对话',
  '/digital-person': '3D 数字人',
  '/memories/create': '创建记忆',
  '/memories/query': '查询记忆',
  '/memories/cleanup': '记忆清理',
  '/jobs': '生成任务',
  '/rag': 'Memory RAG 检索',
  '/profiles': '用户画像',
  '/full-context': 'Full Context 测试',
  '/knowledge': '知识集合',
  '/knowledge/collections': '知识集合',
  '/knowledge/documents': '知识文档',
  '/knowledge/rag': 'Knowledge RAG 检索',
  '/graph': '知识图谱',
  '/tenants': '多租户管理',
  '/system': '系统状态',
  '/stream-test': '流式响应测试',
}

function AppShell() {
  const location = useLocation()
  const pageTitle = pageTitles[location.pathname] || 'memRagAgent'

  return (
    <div className="app-container">
      <Sidebar />
      
      <div className="main-content">
        <header className="topbar">
          <div className="topbar-title">{pageTitle}</div>
          <div className="topbar-actions">
            <Link to="/">
              <button>🏠 首页</button>
            </Link>
          </div>
        </header>

        <main className="page-content">
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
            <Route path="/tenants" element={<TenantsPage />} />
            <Route path="/system" element={<SystemStatusPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/stream-test" element={<StreamTestPage />} />
            <Route path="*" element={
              <div className="empty-state">
                <div className="empty-state-icon">🔍</div>
                <p>页面不存在</p>
                <Link to="/">返回首页</Link>
              </div>
            } />
          </Routes>
        </main>
      </div>
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