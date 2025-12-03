import { useEffect, useState, type FormEvent } from 'react'
import '../App.css'
import {
  type HealthResponse,
  type QueryResultItem,
  fetchMemoryHealth,
  createMemory,
  queryMemories,
} from '../api/memory'

function MemoriesPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  // create memory form state
  const [cmUserId, setCmUserId] = useState('u_123')
  const [cmProjectId, setCmProjectId] = useState('proj_memRagAgent')
  const [cmType, setCmType] = useState('semantic')
  const [cmText, setCmText] = useState('')
  const [cmTags, setCmTags] = useState('profile, preference')
  const [cmSaving, setCmSaving] = useState(false)
  const [cmMessage, setCmMessage] = useState<string | null>(null)

  // query state
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

  const handleCreateMemory = async (e: FormEvent) => {
    e.preventDefault()
    setCmSaving(true)
    setCmMessage(null)
    try {
      const tagsArray = cmTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)

      await createMemory({
        user_id: cmUserId || undefined,
        project_id: cmProjectId || undefined,
        type: cmType,
        source: 'system',
        text: cmText,
        importance: 0.8,
        tags: tagsArray,
      })

      setCmMessage('Memory created successfully.')
      setCmText('')
    } catch (err) {
      setCmMessage(`Failed: ${(err as Error).message}`)
    } finally {
      setCmSaving(false)
    }
  }

  const runQuery = async () => {
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
        page,
        page_size: pageSize,
        filters: {
          types: ['semantic'],
          tags: tagsArray,
        },
      })

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
    // 每次点“查询”时重置到第 1 页
    setPage(1)
    await runQuery()
  }

  return (
    <div className="page-container">
      <section style={{ marginBottom: '1.5rem' }}>
        <h2 className="section-title">记忆服务健康状态</h2>
        {health && (
          <div>
            <p>Memory Service Status: {health.status}</p>
            <p>Service: {health.service}</p>
            <p>Version: {health.version}</p>
          </div>
        )}
        {healthError && (
          <p style={{ color: 'red' }}>Failed to fetch health: {healthError}</p>
        )}
        {!health && !healthError && <p>Loading health...</p>}
      </section>

      <section className="section-card" style={{ marginBottom: '1rem' }}>
        <h2 className="section-title">植入记忆</h2>
        <form onSubmit={handleCreateMemory} style={{ display: 'grid', gap: '0.5rem' }}>
          <div>
            <label>
              用户 ID:{' '}
              <input
                value={cmUserId}
                onChange={(e) => setCmUserId(e.target.value)}
              />
            </label>
          </div>
          <div>
            <label>
              项目 ID:{' '}
              <input
                value={cmProjectId}
                onChange={(e) => setCmProjectId(e.target.value)}
              />
            </label>
          </div>
          <div>
            <label>
              Type:{' '}
              <select
                value={cmType}
                onChange={(e) => setCmType(e.target.value)}
              >
                <option value="semantic">semantic</option>
                <option value="episodic">episodic</option>
                <option value="working">working</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              Text:
              <br />
              <textarea
                value={cmText}
                onChange={(e) => setCmText(e.target.value)}
                rows={3}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <div>
            <label>
              Tags (comma separated):{' '}
              <input
                value={cmTags}
                onChange={(e) => setCmTags(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <button type="submit" disabled={cmSaving || !cmText.trim()}>
            {cmSaving ? 'Saving...' : 'Create Memory'}
          </button>
        </form>
        {cmMessage && <p style={{ marginTop: '0.5rem' }}>{cmMessage}</p>}
      </section>

      <section className="section-card">
        <h2 className="section-title">查询记忆</h2>
        <form onSubmit={handleQueryMemories} style={{ display: 'grid', gap: '0.5rem' }}>
          <div>
            <label>
              User ID:{' '}
              <input
                value={qUserId}
                onChange={(e) => setQUserId(e.target.value)}
              />
            </label>
          </div>
          <div>
            <label>
              Project ID:{' '}
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
        {qError && <p style={{ color: 'red' }}>Query failed: {qError}</p>}

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
                onClick={async () => {
                  if (page <= 1) return
                  setPage((p) => p - 1)
                  await runQuery()
                }}
              >
                上一页
              </button>
              <button
                type="button"
                disabled={page * pageSize >= total || qLoading}
                onClick={async () => {
                  if (page * pageSize >= total) return
                  setPage((p) => p + 1)
                  await runQuery()
                }}
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

export default MemoriesPage
