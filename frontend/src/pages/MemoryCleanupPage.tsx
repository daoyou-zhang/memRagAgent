import { useState, type FormEvent } from 'react'
import { cleanupMemories, type CleanupMode, type CleanupResponse } from '../api/memoryCleanup'

function MemoryCleanupPage() {
  const [mode, setMode] = useState<CleanupMode>('by_user')
  const [userId, setUserId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [includeEpisodic, setIncludeEpisodic] = useState(true)
  const [includeSemantic, setIncludeSemantic] = useState(true)
  const [before, setBefore] = useState('')
  const [maxKeep, setMaxKeep] = useState(1000)
  const [deleteProfile, setDeleteProfile] = useState(false)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CleanupResponse | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setResult(null)

    const types: ('episodic' | 'semantic')[] = []
    if (includeEpisodic) types.push('episodic')
    if (includeSemantic) types.push('semantic')

    const payload: any = {
      mode,
      user_id: userId || undefined,
      project_id: projectId || undefined,
      types: types.length ? types : undefined,
      delete_profile: deleteProfile || undefined,
    }

    if (mode === 'by_time') {
      payload.before = before || undefined
    }
    if (mode === 'by_limit') {
      payload.max_keep = maxKeep
    }

    setLoading(true)
    try {
      const resp = await cleanupMemories(payload)
      setResult(resp)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 900, margin: '0 auto', display: 'grid', gap: '1rem' }}>
      <h2>记忆清理（手动）</h2>
      <p style={{ fontSize: 13, color: '#555' }}>
        仅针对单个 user_id + 可选 project_id 进行清理。请谨慎操作，删除后无法恢复。
      </p>

      <form onSubmit={handleSubmit} style={{ border: '1px solid #ddd', padding: '0.75rem', borderRadius: 4 }}>
        <div style={{ marginBottom: '0.5rem' }}>
          <label>
            模式 (mode):{' '}
            <select value={mode} onChange={(e) => setMode(e.target.value as CleanupMode)}>
              <option value="by_user">按用户全部删除 (by_user)</option>
              <option value="by_time">按时间删除 (by_time)</option>
              <option value="by_limit">按数量保留 (by_limit)</option>
            </select>
          </label>
        </div>

        <div style={{ marginBottom: '0.5rem' }}>
          <label>
            user_id:{' '}
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              style={{ width: '14rem' }}
              placeholder="必填（by_user/by_limit）"
            />
          </label>
        </div>

        <div style={{ marginBottom: '0.5rem' }}>
          <label>
            project_id:{' '}
            <input value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ width: '14rem' }} />
          </label>
        </div>

        <div style={{ marginBottom: '0.5rem' }}>
          <span>记忆类型：</span>
          <label style={{ marginRight: '0.75rem' }}>
            <input
              type="checkbox"
              checked={includeEpisodic}
              onChange={(e) => setIncludeEpisodic(e.target.checked)}
            />{' '}
            episodic
          </label>
          <label>
            <input
              type="checkbox"
              checked={includeSemantic}
              onChange={(e) => setIncludeSemantic(e.target.checked)}
            />{' '}
            semantic
          </label>
        </div>

        {mode === 'by_time' && (
          <div style={{ marginBottom: '0.5rem' }}>
            <label>
              删除此时间之前的记忆 (before, ISO 格式):{' '}
              <input
                value={before}
                onChange={(e) => setBefore(e.target.value)}
                style={{ width: '20rem' }}
                placeholder="例如 2024-01-01T00:00:00"
              />
            </label>
          </div>
        )}

        {mode === 'by_limit' && (
          <div style={{ marginBottom: '0.5rem' }}>
            <label>
              仅保留最近 max_keep 条记忆:{' '}
              <input
                type="number"
                value={maxKeep}
                onChange={(e) => setMaxKeep(Number(e.target.value) || 0)}
                style={{ width: '8rem' }}
                min={1}
              />
            </label>
          </div>
        )}

        <div style={{ marginBottom: '0.5rem' }}>
          <label>
            <input
              type="checkbox"
              checked={deleteProfile}
              onChange={(e) => setDeleteProfile(e.target.checked)}
            />{' '}
            同时删除该用户在该 project 下的画像（Profile + 历史画像）
          </label>
        </div>

        <button type="submit" disabled={loading || (mode !== 'by_time' && !userId.trim())}>
          {loading ? '执行中...' : '执行清理'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>错误: {error}</p>}

      {result && (
        <section style={{ border: '1px solid #ddd', padding: '0.75rem', borderRadius: 4 }}>
          <h3>清理结果</h3>
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>{JSON.stringify(result, null, 2)}</pre>
        </section>
      )}
    </div>
  )
}

export default MemoryCleanupPage
