import { BrowserRouter, Link, Route, Routes, Navigate } from 'react-router-dom'
import './App.css'
import MemoryCreatePage from './pages/MemoryCreatePage'
import MemoryQueryPage from './pages/MemoryQueryPage'
import RagPage from './pages/RagPage'
import ProfilesPage from './pages/ProfilesPage'
import JobsPage from './pages/JobsPage'
import FullContextPage from './pages/FullContextPage'

function App() {
  return (
    <BrowserRouter>
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
          <nav className="app-nav" style={{ display: 'flex', gap: '1rem' }}>
            <Link to="/memories/create">创建记忆</Link>
            <Link to="/memories/query">查询记忆</Link>
            <Link to="/jobs">Episodic Jobs</Link>
            <Link to="/rag">RAG</Link>
            <Link to="/profiles">Profiles</Link>
            <Link to="/full-context">Full Context</Link>
          </nav>
        </header>

        <main style={{ flex: 1, padding: '1rem' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/memories/create" replace />} />
            <Route path="/memories/create" element={<MemoryCreatePage />} />
            <Route path="/memories/query" element={<MemoryQueryPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/rag" element={<RagPage />} />
            <Route path="/profiles" element={<ProfilesPage />} />
            <Route path="/full-context" element={<FullContextPage />} />
            <Route path="*" element={<div>Not Found</div>} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App