import { useState, type FormEvent } from 'react'
import { fetchFullContext, type FullContextResponse } from '../api/memory'

function FullContextPage() {
  const [projectId, setProjectId] = useState('DAOYOUTEST')
  const [userId, setUserId] = useState('48eedcd8-ed89-464c-8109-7bcb6fe94e36')
  const [sessionId, setSessionId] = useState('ced440f3-90d2-48be-a651-b7da0b2dcb91')
  const [query, setQuery] = useState('')
  const [recentLimit, setRecentLimit] = useState<number | ''>('')
  const [ragTopK, setRagTopK] = useState<number | ''>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<FullContextResponse | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!projectId.trim() || !sessionId.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await fetchFullContext({
        project_id: projectId,
        user_id: userId || undefined,
        session_id: sessionId,
        query: query || undefined,
        recent_message_limit:
          typeof recentLimit === 'number' && !Number.isNaN(recentLimit)
            ? recentLimit
            : undefined,
        rag_top_k:
          typeof ragTopK === 'number' && !Number.isNaN(ragTopK) ? ragTopK : undefined,
      })
      setResult(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 1100, margin: '0 auto' }}>
      <h2>Full Context Playground</h2>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.5rem' }}>
        <div>
          <label>
            Project ID:{' '}
            <input value={projectId} onChange={(e) => setProjectId(e.target.value)} />
          </label>
        </div>
        <div>
          <label>
            User ID:{' '}
            <input value={userId} onChange={(e) => setUserId(e.target.value)} />
          </label>
        </div>
        <div>
          <label>
            Session ID:{' '}
            <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
          </label>
        </div>
        <div>
          <label>
            Query (用于 RAG，可为空):
            <br />
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              style={{ width: '100%' }}
            />
          </label>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <label>
            recent_message_limit:{' '}
            <input
              type="number"
              min={1}
              value={recentLimit}
              onChange={(e) => {
                const v = e.target.value
                setRecentLimit(v === '' ? '' : Number(v))
              }}
              style={{ width: '6rem' }}
            />
          </label>
          <label>
            rag_top_k:{' '}
            <input
              type="number"
              min={1}
              max={50}
              value={ragTopK}
              onChange={(e) => {
                const v = e.target.value
                setRagTopK(v === '' ? '' : Number(v))
              }}
              style={{ width: '6rem' }}
            />
          </label>
        </div>
        <button type="submit" disabled={loading || !projectId.trim() || !sessionId.trim()}>
          {loading ? 'Loading...' : 'Fetch Full Context'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {result && (
        <div style={{ marginTop: '1rem', display: 'grid', gap: '1rem' }}>
          <section>
            <h3>Profile</h3>
            <pre
              style={{
                background: '#f5f5f5',
                padding: '0.75rem',
                maxHeight: 260,
                overflow: 'auto',
                fontSize: 12,
              }}
            >
              {JSON.stringify(result.profile, null, 2)}
            </pre>
          </section>

          <section>
            <h3>Working Messages (最近对话)</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>#</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Role</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Time</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Content</th>
                </tr>
              </thead>
              <tbody>
                {result.working_messages.map((m, idx) => (
                  <tr key={m.id}>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>{idx + 1}</td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>{m.role}</td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>{m.created_at}</td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>{m.content}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h3>RAG Memories</h3>
            <p style={{ fontSize: 12, color: '#555' }}>
              candidates: {result.rag_debug.total_candidates}, top_k:{' '}
              {result.rag_debug.top_k}, avg_sim:{' '}
              {typeof result.rag_debug.avg_similarity_top_k === 'number'
                ? result.rag_debug.avg_similarity_top_k.toFixed(3)
                : '-'}
              , avg_score:{' '}
              {typeof result.rag_debug.avg_score_top_k === 'number'
                ? result.rag_debug.avg_score_top_k.toFixed(3)
                : '-'}
            </p>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>#</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Type</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Score</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Sim</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Imp</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Recency</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Text</th>
                </tr>
              </thead>
              <tbody>
                {result.rag_memories.map((m, idx) => (
                  <tr key={m.id}>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>{idx + 1}</td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                      {m.memory_type || m.type}
                    </td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                      {typeof m.score === 'number' ? m.score.toFixed(3) : '-'}
                    </td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                      {typeof m.similarity === 'number' ? m.similarity.toFixed(3) : '-'}
                    </td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                      {typeof m.importance === 'number' ? m.importance.toFixed(3) : '-'}
                    </td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                      {typeof m.recency === 'number' ? m.recency.toFixed(3) : '-'}
                    </td>
                    <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>{m.text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </div>
  )
}

export default FullContextPage
