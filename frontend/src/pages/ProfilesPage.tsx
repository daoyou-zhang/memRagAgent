import { useState, type FormEvent } from 'react'
import { getUserProfile, type RawProfilePayload } from '../api/profiles'

function ProfilesPage() {
  const [userId, setUserId] = useState('48eedcd8-ed89-464c-8109-7bcb6fe94e36')
  const [projectId, setProjectId] = useState('DAOYOUTEST')
  const [forceRefresh, setForceRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [profile, setProfile] = useState<RawProfilePayload | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setProfile(null)
    try {
      const data = await getUserProfile(userId, projectId || undefined, forceRefresh)
      setProfile(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 900, margin: '0 auto' }}>
      <h2>User Profile (from /api/profiles)</h2>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.5rem' }}>
        <div>
          <label>
            User ID:{' '}
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </label>
        </div>
        <div>
          <label>
            Project ID (可选):{' '}
            <input
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            />
          </label>
        </div>
        <div>
          <label>
            <input
              type="checkbox"
              checked={forceRefresh}
              onChange={(e) => setForceRefresh(e.target.checked)}
            />{' '}
            强制刷新画像（本次请求一定调用大模型聚合）
          </label>
        </div>
        <button type="submit" disabled={loading || !userId.trim()}>
          {loading ? 'Loading...' : 'Load Profile'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {profile && (
        <div style={{ marginTop: '1rem' }}>
          <h3>
            User: {profile.user_id}{' '}
            {profile.project_id && <span>(project: {profile.project_id})</span>}
          </h3>
          <p className="muted-text">当前为 MVP：直接展示 raw_semantic_memories，后续会接入 LLM 聚合为结构化画像。</p>
          <pre style={{ background: '#f5f5f5', padding: '0.75rem', overflowX: 'auto' }}>
            {JSON.stringify(profile.profile, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default ProfilesPage
