import { useEffect, useState, type FormEvent } from 'react'
import '../App.css'
import {
  fetchMemoryHealth,
  queryMemories,
  type HealthResponse,
  type QueryResultItem,
} from '../api/memory'

function MemoryQueryPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  const [qUserId, setQUserId] = useState('u_123')
  const [qProjectId, setQProjectId] = useState('proj_memRagAgent')
  const [qText, setQText] = useState('')
  const [qTags, setQTags] = useState('profile')
  const [qLoading, setQLoading] = useState(false)
  const [qError, setQError] = useState<string | null>(null)
  const [qItems, setQItems] = useState<QueryResultItem[]>([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const data = await fetchMemoryHealth()
        setHealth(data)
      } catch (err) {
        setHealthError((err as Error).message)
      }
    }

    loadHealth()
  }, [])

  const runQuery = async (targetPage: number) => {
    setQLoading(true)
    setQError(null)
    try {
      const tagsArray = qTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)

      const data = await queryMemories({
        user_id: qUserId || undefined,
        project_id: qProjectId || undefined,
        query: qText || undefined,
        top_k: 0,
        page: targetPage,
        page_size: pageSize,
        filters: {
          types: ['semantic'],
          tags: tagsArray,
        },
      })

      setPage(data.page)
      setQItems(data.items || [])
      setTotal(data.total ?? 0)
    } catch (err) {
      setQError((err as Error).message)
    } finally {
      setQLoading(false)
    }
  }

  const handleQueryMemories = async (e: FormEvent) => {
    e.preventDefault()
    await runQuery(1)
  }

  const handlePrevPage = async () => {
    if (page <= 1 || qLoading) return
    await runQuery(page - 1)
  }

  const handleNextPage = async () => {
    if (page * pageSize >= total || qLoading) return
    await runQuery(page + 1)
  }

  return (
    <div className="page-container">
      <section style={{ marginBottom: '1.5rem' }}>
        <h2 className="section-title">记忆服务健康状态</h2>
        {health && (
          <div>
            <p>状态: {health.status}</p>
            <p>服务: {health.service}</p>
            <p>版本: {health.version}</p>
          </div>
        )}
        {healthError && (
          <p style={{ color: 'red' }}>健康检查失败: {healthError}</p>
        )}
        {!health && !healthError && <p className="muted-text">加载中...</p>}
      </section>

      <section className="section-card">
        <h2 className="section-title">查询记忆</h2>
        <form onSubmit={handleQueryMemories} style={{ display: 'grid', gap: '0.5rem' }}>
          <div>
            <label>
              用户 ID:{' '}
              <input
                value={qUserId}
                onChange={(e) => setQUserId(e.target.value)}
              />
            </label>
          </div>
          <div>
            <label>
              项目 ID:{' '}
              <input
                value={qProjectId}
                onChange={(e) => setQProjectId(e.target.value)}
              />
            </label>
          </div>
          <div>
            <label>
              查询内容:{' '}
              <input
                value={qText}
                onChange={(e) => setQText(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <div>
            <label>
              标签筛选（逗号分隔）:{' '}
              <input
                value={qTags}
                onChange={(e) => setQTags(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <button type="submit" disabled={qLoading}>
            {qLoading ? '查询中...' : '查询记忆'}
          </button>
        </form>
        {qError && <p style={{ color: 'red' }}>查询失败: {qError}</p>}

        <div style={{ marginTop: '1rem' }}>
          <h3>结果列表（本页 {qItems.length} 条）</h3>
          {qItems.length === 0 && <p>暂无匹配的记忆。</p>}
          {qItems.length > 0 && (
            <table className="results-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>类型</th>
                  <th>重要度</th>
                  <th>内容</th>
                  <th>标签</th>
                  <th>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {qItems.map((item) => (
                  <tr key={item.memory.id}>
                    <td>{item.memory.id}</td>
                    <td>{item.memory.type}</td>
                    <td>{item.memory.importance}</td>
                    <td>{item.memory.text}</td>
                    <td>
                      {Array.isArray(item.memory.tags)
                        ? item.memory.tags.join(', ')
                        : ''}
                    </td>
                    <td>{item.memory.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {total > 0 && (
            <div
              className="muted-text"
              style={{ marginTop: '0.5rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}
            >
              <span>
                第 {page} 页 / 共 {Math.max(1, Math.ceil(total / pageSize))} 页，合计 {total} 条
              </span>
              <button
                type="button"
                disabled={page <= 1 || qLoading}
                onClick={handlePrevPage}
              >
                上一页
              </button>
              <button
                type="button"
                disabled={page * pageSize >= total || qLoading}
                onClick={handleNextPage}
              >
                下一页
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

export default MemoryQueryPage
