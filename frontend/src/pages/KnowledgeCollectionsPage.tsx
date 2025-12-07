import { useEffect, useState, type FormEvent } from 'react'
import { listCollections, createCollection, type KnowledgeCollection } from '../api/knowledge'

function KnowledgeCollectionsPage() {
  const [collections, setCollections] = useState<KnowledgeCollection[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [projectId, setProjectId] = useState('DAOYOUTEST')
  const [domainFilter, setDomainFilter] = useState('')

  const [newName, setNewName] = useState('示例知识库')
  const [newDomain, setNewDomain] = useState('law')
  const [newDescription, setNewDescription] = useState('法律 / 心理 / 话术 / 医疗 等通用结构')

  const loadCollections = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await listCollections({ project_id: projectId || undefined, domain: domainFilter || undefined })
      setCollections(resp.items || [])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadCollections()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!newName.trim() || !newDomain.trim()) return
    setError(null)
    try {
      await createCollection({
        project_id: projectId || undefined,
        name: newName.trim(),
        domain: newDomain.trim(),
        description: newDescription || undefined,
      })
      setNewName('')
      await loadCollections()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 1000, margin: '0 auto', display: 'grid', gap: '1rem' }}>
      <h2>知识集合管理</h2>

      <section style={{ border: '1px solid #ddd', padding: '0.75rem', borderRadius: 4 }}>
        <h3>创建集合</h3>
        <form onSubmit={handleCreate} style={{ display: 'grid', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <div>
            <label>
              project_id:{' '}
              <input
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                style={{ width: '16rem' }}
              />
            </label>
          </div>
          <div>
            <label>
              名称 (name):{' '}
              <input value={newName} onChange={(e) => setNewName(e.target.value)} style={{ width: '16rem' }} />
            </label>
          </div>
          <div>
            <label>
              领域 (domain):{' '}
              <input
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                style={{ width: '10rem' }}
                placeholder="law / psychology / sales_script / medical_terms"
              />
            </label>
          </div>
          <div>
            <label>
              描述:{' '}
              <input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <button type="submit" disabled={!newName.trim() || !newDomain.trim()}>
            创建集合
          </button>
        </form>

        {error && <p style={{ color: 'red' }}>错误: {error}</p>}
      </section>

      <section style={{ border: '1px solid #ddd', padding: '0.75rem', borderRadius: 4 }}>
        <h3>集合列表</h3>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
          <label>
            过滤 project_id:{' '}
            <input value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ width: '10rem' }} />
          </label>
          <label>
            过滤 domain:{' '}
            <input value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)} style={{ width: '8rem' }} />
          </label>
          <button type="button" onClick={() => void loadCollections()}>
            刷新
          </button>
        </div>
        {loading && <p>加载中...</p>}
        {!loading && collections.length === 0 && <p>暂无集合。</p>}
        {collections.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>#</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>名称</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>领域</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>项目</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>描述</th>
              </tr>
            </thead>
            <tbody>
              {collections.map((c, idx) => (
                <tr key={c.id}>
                  <td style={{ padding: '0.25rem 0.5rem' }}>{idx + 1}</td>
                  <td style={{ padding: '0.25rem 0.5rem' }}>{c.name}</td>
                  <td style={{ padding: '0.25rem 0.5rem' }}>{c.domain}</td>
                  <td style={{ padding: '0.25rem 0.5rem' }}>{c.project_id}</td>
                  <td style={{ padding: '0.25rem 0.5rem' }}>{c.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}

export default KnowledgeCollectionsPage
