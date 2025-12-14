import { useEffect, useState, type FormEvent } from 'react'
import { listCollections, type KnowledgeCollection } from '../api/knowledge'
import { knowledgeRagQuery, type KnowledgeRagResponse } from '../api/knowledgeRag'

function KnowledgeRagPage() {
  const [projectId, setProjectId] = useState('')
  const [domain, setDomain] = useState('')
  const [collections, setCollections] = useState<KnowledgeCollection[]>([])
  const [selectedCollectionIds, setSelectedCollectionIds] = useState<number[]>([])

  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(8)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<KnowledgeRagResponse | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await listCollections({ project_id: projectId || undefined, domain: domain || undefined })
        setCollections(resp.items || [])
      } catch (err) {
        console.error(err)
      }
    }
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const payload: any = {
        query,
        top_k: topK || undefined,
        project_id: projectId || undefined,
        domain: domain || undefined,
      }
      if (selectedCollectionIds.length) {
        payload.collection_ids = selectedCollectionIds
      }
      const data = await knowledgeRagQuery(payload)
      setResult(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const toggleCollectionId = (id: number) => {
    setSelectedCollectionIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 1000, margin: '0 auto' }}>
      <h2>知识库 RAG 检索实验台</h2>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.5rem' }}>
        <div>
          <label>
            project_id:{' '}
            <input value={projectId} onChange={(e) => setProjectId(e.target.value)} />
          </label>
        </div>
        <div>
          <label>
            domain:{' '}
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="law / psychology / ..."
            />
          </label>
        </div>
        <div>
          <label>
            选择集合（多选）:
            <br />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.25rem' }}>
              {collections.length === 0 && <span className="muted-text">暂无集合或尚未加载。</span>}
              {collections.map((c) => (
                <label key={c.id} style={{ border: '1px solid #ddd', padding: '0.25rem 0.5rem', borderRadius: 4 }}>
                  <input
                    type="checkbox"
                    checked={selectedCollectionIds.includes(c.id)}
                    onChange={() => toggleCollectionId(c.id)}
                  />{' '}
                  {c.id} - {c.name} ({c.domain})
                </label>
              ))}
            </div>
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
          {loading ? '查询中...' : '执行知识库 RAG 检索'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>错误: {error}</p>}

      {result && (
        <div style={{ marginTop: '1rem' }}>
          <h3>命中的 Chunks</h3>
          <p className="muted-text">
            total_candidates={result.debug.total_candidates}, top_k={result.debug.top_k}, avg_sim={
              result.debug.avg_similarity_top_k.toFixed(3)
            }
          </p>
          {result.used_chunks.length === 0 && <p>暂无结果。</p>}
          {result.used_chunks.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>#</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>集合</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>domain</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>section</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>score</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>sim</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>imp</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>text（前 80 字）</th>
                </tr>
              </thead>
              <tbody>
                {result.used_chunks.map((c, idx) => (
                  <tr key={c.id}>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{idx + 1}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{c.collection_name}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{c.domain}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{c.section_label || '-'}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{c.score.toFixed(3)}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{c.similarity.toFixed(3)}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{c.importance.toFixed(3)}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>
                      {c.text.length > 80 ? `${c.text.slice(0, 80)}...` : c.text}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

export default KnowledgeRagPage
