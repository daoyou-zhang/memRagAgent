import { Link } from 'react-router-dom'

const cards = [
  {
    to: '/cognitive',
    icon: '💬',
    title: '认知对话',
    desc: '与 AI 进行智能对话，支持记忆、RAG、工具调用',
    color: '#10b981',
  },
  {
    to: '/memories/query',
    icon: '🧠',
    title: '记忆管理',
    desc: '管理 episodic 和 semantic 记忆，查看用户画像',
    color: '#6366f1',
  },
  {
    to: '/knowledge/collections',
    icon: '📚',
    title: '知识库',
    desc: '管理多领域知识集合、文档分块、向量检索',
    color: '#f59e0b',
  },
  {
    to: '/graph',
    icon: '🕸️',
    title: '知识图谱',
    desc: '可视化查看知识实体与关系网络',
    color: '#ec4899',
  },
]

const quickLinks = [
  { to: '/jobs', label: '生成任务', icon: '⚙️' },
  { to: '/rag', label: 'Memory RAG', icon: '🔍' },
  { to: '/full-context', label: 'Full Context', icon: '📋' },
  { to: '/profiles', label: '用户画像', icon: '👤' },
]

function HomePage() {
  return (
    <div className="fade-in" style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* 欢迎区 */}
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
          👋 欢迎使用 memRagAgent
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>
          认知记忆增强的 AI 对话系统
        </p>
      </div>

      {/* 主要功能卡片 */}
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        {cards.map((card, i) => (
          <Link
            key={i}
            to={card.to}
            className="card"
            style={{
              textDecoration: 'none',
              transition: 'all 0.2s',
              cursor: 'pointer',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = card.color
              e.currentTarget.style.transform = 'translateY(-2px)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--border-color)'
              e.currentTarget.style.transform = 'translateY(0)'
            }}
          >
            <div style={{ 
              fontSize: '2.5rem', 
              marginBottom: '0.75rem',
              filter: 'grayscale(0)',
            }}>
              {card.icon}
            </div>
            <h3 style={{ 
              margin: '0 0 0.5rem', 
              color: 'var(--text-primary)',
              fontSize: '1.125rem',
            }}>
              {card.title}
            </h3>
            <p style={{ 
              margin: 0, 
              color: 'var(--text-secondary)', 
              fontSize: '0.875rem',
              lineHeight: 1.5,
            }}>
              {card.desc}
            </p>
          </Link>
        ))}
      </div>

      {/* 快捷入口 */}
      <div className="card">
        <h3 style={{ margin: '0 0 1rem', fontSize: '1rem' }}>快捷入口</h3>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {quickLinks.map((link, i) => (
            <Link key={i} to={link.to}>
              <button>
                <span>{link.icon}</span>
                <span>{link.label}</span>
              </button>
            </Link>
          ))}
          <a
            href="http://localhost:8000/test/stream"
            target="_blank"
            rel="noopener noreferrer"
          >
            <button>
              <span>🌊</span>
              <span>流式测试</span>
            </button>
          </a>
        </div>
      </div>

      {/* 系统状态 */}
      <div style={{ 
        marginTop: '2rem', 
        padding: '1rem', 
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
      }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem',
          fontSize: '0.875rem',
          color: 'var(--text-secondary)',
        }}>
          <span style={{ 
            width: 8, 
            height: 8, 
            borderRadius: '50%', 
            backgroundColor: '#10b981',
          }} />
          <span>系统运行正常</span>
          <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>
            Memory: :5000 | Knowledge: :5001 | Agent: :8000
          </span>
        </div>
      </div>
    </div>
  )
}

export default HomePage
