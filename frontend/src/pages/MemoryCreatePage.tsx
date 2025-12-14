import { useEffect, useState, type FormEvent } from 'react'
import '../App.css'
import { fetchMemoryHealth, createMemory, type HealthResponse } from '../api/memory'

function MemoryCreatePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  const [cmUserId, setCmUserId] = useState('')
  const [cmProjectId, setCmProjectId] = useState('')
  const [cmType, setCmType] = useState('semantic')
  const [cmText, setCmText] = useState('')
  const [cmTags, setCmTags] = useState('profile, preference')
  const [cmSaving, setCmSaving] = useState(false)
  const [cmMessage, setCmMessage] = useState<string | null>(null)

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

      setCmMessage('记忆已成功写入。')
      setCmText('')
    } catch (err) {
      setCmMessage(`写入失败: ${(err as Error).message}`)
    } finally {
      setCmSaving(false)
    }
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
              记忆类型:{' '}
              <select
                value={cmType}
                onChange={(e) => setCmType(e.target.value)}
              >
                <option value="semantic">语义记忆 (semantic)</option>
                <option value="episodic">情节记忆 (episodic)</option>
                <option value="working">工作记忆 (working)</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              记忆内容:
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
              标签（逗号分隔）:{' '}
              <input
                value={cmTags}
                onChange={(e) => setCmTags(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <p className="muted-text">
            建议：语义记忆尽量用一句话描述清晰结论，例如“用户偏好：回答时先给结论再解释。”
          </p>
          <button type="submit" disabled={cmSaving || !cmText.trim()}>
            {cmSaving ? '写入中...' : '写入记忆'}
          </button>
        </form>
        {cmMessage && <p style={{ marginTop: '0.5rem' }}>{cmMessage}</p>}
      </section>
    </div>
  )
}

export default MemoryCreatePage
