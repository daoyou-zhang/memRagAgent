import { Link } from 'react-router-dom'

function HomePage() {
  return (
    <div
      style={{
        padding: '2rem',
        maxWidth: 900,
        margin: '0 auto',
        display: 'grid',
        gap: '1.5rem',
      }}
    >
      <h2>请选择要进入的控制台</h2>
      <p style={{ fontSize: 14, color: '#555' }}>
        本系统包含两大子模块：个人记忆服务（Memory Service）与通用知识库（Knowledge Service）。
      </p>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '1rem',
        }}
      >
        <Link
          to="/memories/create"
          style={{
            border: '1px solid #ddd',
            borderRadius: 8,
            padding: '1.25rem',
            textDecoration: 'none',
            color: 'inherit',
            background: '#f7f9ff',
          }}
        >
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>记忆控制台</h3>
          <p style={{ margin: 0, fontSize: 13, color: '#555' }}>
            管理用户会话记忆、画像、Memory-RAG 以及 Full Context 实验台。
          </p>
        </Link>
        <Link
          to="/knowledge"
          style={{
            border: '1px solid #ddd',
            borderRadius: 8,
            padding: '1.25rem',
            textDecoration: 'none',
            color: 'inherit',
            background: '#f8f8f8',
          }}
        >
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>知识库管理</h3>
          <p style={{ margin: 0, fontSize: 13, color: '#555' }}>
            管理多领域知识集合与文档（法律、心理学、企业话术、医院术语等）。
          </p>
        </Link>
      </div>
    </div>
  )
}

export default HomePage
