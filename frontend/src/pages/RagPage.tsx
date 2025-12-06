import { useState, type FormEvent } from 'react'
import { ragQuery, type RagQueryResponse } from '../api/rag'

function RagPage() {
  const [projectId, setProjectId] = useState('DAOYOUTEST')
  const [userId, setUserId] = useState('48eedcd8-ed89-464c-8109-7bcb6fe94e36')
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(8)
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
        top_k: topK || undefined,
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
      <h2>RAG 检索实验台</h2>
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
        <div>
          <label>
            top_k:{' '}
            <input
              type="number"
              min={1}
              max={50}
              value={topK}
              onChange={(e) =>
                setTopK(Number.isNaN(Number(e.target.value)) ? 0 : Number(e.target.value))
              }
              style={{ width: '5rem' }}
            />
          </label>
        </div>
        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? '查询中...' : '执行 RAG 检索'}
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
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
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
                  {result.used_context.map((c, idx) => (
                    <tr key={c.type + ':' + c.id}>
                      <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>{idx + 1}</td>
                      <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                        {c.memory_type || c.type}
                      </td>
                      <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                        {c.score.toFixed(3)}
                      </td>
                      <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                        {c.similarity !== undefined ? c.similarity.toFixed(3) : '-'}
                      </td>
                      <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                        {c.importance !== undefined ? c.importance.toFixed(3) : '-'}
                      </td>
                      <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>
                        {c.recency !== undefined ? c.recency.toFixed(3) : '-'}
                      </td>
                      <td style={{ verticalAlign: 'top', padding: '0.25rem 0.5rem' }}>{c.text}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default RagPage
