import { useState, type FormEvent } from 'react'
import { ragQuery, type RagQueryResponse } from '../api/rag'

function RagPage() {
  const [projectId, setProjectId] = useState('proj_memRagAgent')
  const [userId, setUserId] = useState('u_123')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RagQueryResponse | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await ragQuery({
        project_id: projectId,
        user_id: userId || undefined,
        query,
      })
      setResult(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 900, margin: '0 auto' }}>
      <h2>RAG Playground</h2>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.5rem' }}>
        <div>
          <label>
            Project ID:{' '}
            <input
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            />
          </label>
        </div>
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
            Query:
            <br />
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              style={{ width: '100%' }}
            />
          </label>
        </div>
        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? 'Querying...' : 'Run RAG Query'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {result && (
        <div style={{ marginTop: '1rem' }}>
          <h3>Answer</h3>
          <p>{result.answer}</p>
          {result.used_context && (
            <>
              <h4>Used Context</h4>
              <ul>
                {result.used_context.map((c) => (
                  <li key={c.type + ':' + c.id}>
                    <strong>[{c.type}]</strong> {c.text} (score: {c.score})
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default RagPage
