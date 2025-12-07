import { useEffect, useState, type FormEvent } from 'react'
import {
  listCollections,
  createCollection,
  listDocuments,
  createDocument,
  type KnowledgeCollection,
  type KnowledgeDocument,
  type KnowledgeChunk,
  indexDocument,
  listChunks,
} from '../api/knowledge'

function KnowledgePage() {
  const [collections, setCollections] = useState<KnowledgeCollection[]>([])
  const [loadingCollections, setLoadingCollections] = useState(false)
  const [collectionError, setCollectionError] = useState<string | null>(null)

  const [newColProjectId, setNewColProjectId] = useState('DAOYOUTEST')
  const [newColName, setNewColName] = useState('示例知识库')
  const [newColDomain, setNewColDomain] = useState('law')
  const [newColDescription, setNewColDescription] = useState('法律 / 心理 / 话术 / 医疗 等通用结构')

  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null)
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const [documentError, setDocumentError] = useState<string | null>(null)

  const [activeChunksDocId, setActiveChunksDocId] = useState<number | null>(null)
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([])
  const [loadingChunks, setLoadingChunks] = useState(false)
  const [chunksError, setChunksError] = useState<string | null>(null)

  const [newDocTitle, setNewDocTitle] = useState('示例文档')
  const [newDocExternalId, setNewDocExternalId] = useState('')
  const [newDocSourceUri, setNewDocSourceUri] = useState('')

  const loadCollections = async () => {
    setLoadingCollections(true)
    setCollectionError(null)
    try {
      const resp = await listCollections()
      setCollections(resp.items || [])
      // 如果当前无选中集合，但有数据，则默认选中第一个
      if (!selectedCollectionId && resp.items && resp.items.length > 0) {
        setSelectedCollectionId(resp.items[0].id)
      }
    } catch (err) {
      setCollectionError((err as Error).message)
    } finally {
      setLoadingCollections(false)
    }
  }

  useEffect(() => {
    void loadCollections()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadDocuments = async (collectionId: number | null) => {
    if (!collectionId) {
      setDocuments([])
      return
    }
    setLoadingDocuments(true)
    setDocumentError(null)
    try {
      const resp = await listDocuments({ collection_id: collectionId })
      setDocuments(resp.items || [])
    } catch (err) {
      setDocumentError((err as Error).message)
    } finally {
      setLoadingDocuments(false)
    }
  }

  useEffect(() => {
    void loadDocuments(selectedCollectionId)
  }, [selectedCollectionId])

  const handleCreateCollection = async (e: FormEvent) => {
    e.preventDefault()
    if (!newColName.trim() || !newColDomain.trim()) return
    setCollectionError(null)
    try {
      await createCollection({
        project_id: newColProjectId || undefined,
        name: newColName.trim(),
        domain: newColDomain.trim(),
        description: newColDescription || undefined,
      })
      setNewColName('')
      await loadCollections()
    } catch (err) {
      setCollectionError((err as Error).message)
    }
  }

  const handleCreateDocument = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedCollectionId || !newDocTitle.trim()) return
    setDocumentError(null)
    try {
      await createDocument({
        collection_id: selectedCollectionId,
        title: newDocTitle.trim(),
        external_id: newDocExternalId || undefined,
        source_uri: newDocSourceUri || undefined,
      })
      setNewDocTitle('')
      setNewDocExternalId('')
      setNewDocSourceUri('')
      await loadDocuments(selectedCollectionId)
    } catch (err) {
      setDocumentError((err as Error).message)
    }
  }

  const handleIndexDocument = async (docId: number) => {
    setDocumentError(null)
    try {
      await indexDocument(docId)
      if (selectedCollectionId) {
        await loadDocuments(selectedCollectionId)
      }
    } catch (err) {
      setDocumentError((err as Error).message)
    }
  }

  const handleViewChunks = async (docId: number) => {
    if (activeChunksDocId === docId) {
      // toggle off
      setActiveChunksDocId(null)
      setChunks([])
      setChunksError(null)
      return
    }
    setActiveChunksDocId(docId)
    setLoadingChunks(true)
    setChunksError(null)
    try {
      const resp = await listChunks(docId)
      setChunks(resp.items || [])
    } catch (err) {
      setChunksError((err as Error).message)
    } finally {
      setLoadingChunks(false)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 1100, margin: '0 auto', display: 'grid', gap: '1rem' }}>
      <h2>知识库管理（集合 + 文档）</h2>

      <section style={{ border: '1px solid #ddd', padding: '0.75rem', borderRadius: 4 }}>
        <h3>知识集合（Collections）</h3>
        <form onSubmit={handleCreateCollection} style={{ display: 'grid', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <div>
            <label>
              project_id:{' '}
              <input
                value={newColProjectId}
                onChange={(e) => setNewColProjectId(e.target.value)}
                style={{ width: '16rem' }}
              />
            </label>
          </div>
          <div>
            <label>
              名称 (name):{' '}
              <input
                value={newColName}
                onChange={(e) => setNewColName(e.target.value)}
                style={{ width: '16rem' }}
              />
            </label>
          </div>
          <div>
            <label>
              领域 (domain):{' '}
              <input
                value={newColDomain}
                onChange={(e) => setNewColDomain(e.target.value)}
                style={{ width: '10rem' }}
                placeholder="law / psychology / sales_script / medical_terms"
              />
            </label>
          </div>
          <div>
            <label>
              描述:{' '}
              <input
                value={newColDescription}
                onChange={(e) => setNewColDescription(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <button type="submit" disabled={!newColName.trim() || !newColDomain.trim()}>
            创建集合
          </button>
        </form>

        {collectionError && <p style={{ color: 'red' }}>错误: {collectionError}</p>}

        <div>
          <h4>已存在的集合</h4>
          {loadingCollections && <p>加载中...</p>}
          {!loadingCollections && collections.length === 0 && <p>暂无集合。</p>}
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
                  <tr
                    key={c.id}
                    style={{
                      cursor: 'pointer',
                      background: selectedCollectionId === c.id ? '#f0f4ff' : undefined,
                    }}
                    onClick={() => setSelectedCollectionId(c.id)}
                  >
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
        </div>
      </section>

      <section style={{ border: '1px solid #ddd', padding: '0.75rem', borderRadius: 4 }}>
        <h3>文档（Documents）</h3>
        {!selectedCollectionId && <p>请先在上方选择一个集合。</p>}
        {selectedCollectionId && (
          <>
            <form
              onSubmit={handleCreateDocument}
              style={{ display: 'grid', gap: '0.5rem', marginBottom: '0.75rem' }}
            >
              <div>
                当前集合 ID: <strong>{selectedCollectionId}</strong>
              </div>
              <div>
                <label>
                  标题 (title):{' '}
                  <input
                    value={newDocTitle}
                    onChange={(e) => setNewDocTitle(e.target.value)}
                    style={{ width: '100%' }}
                  />
                </label>
              </div>
              <div>
                <label>
                  external_id:{' '}
                  <input
                    value={newDocExternalId}
                    onChange={(e) => setNewDocExternalId(e.target.value)}
                    style={{ width: '50%' }}
                  />
                </label>
              </div>
              <div>
                <label>
                  source_uri (文件路径或 URL):{' '}
                  <input
                    value={newDocSourceUri}
                    onChange={(e) => setNewDocSourceUri(e.target.value)}
                    style={{ width: '100%' }}
                  />
                </label>
              </div>
              <button type="submit" disabled={!newDocTitle.trim()}>
                创建文档
              </button>
            </form>

            {documentError && <p style={{ color: 'red' }}>错误: {documentError}</p>}

            <div>
              <h4>该集合下的文档</h4>
              {loadingDocuments && <p>加载中...</p>}
              {!loadingDocuments && documents.length === 0 && <p>暂无文档。</p>}
              {documents.length > 0 && (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr>
                      <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>ID</th>
                      <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>标题</th>
                      <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>external_id</th>
                      <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>source_uri</th>
                      <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>status</th>
                      <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((d) => (
                      <tr key={d.id}>
                        <td style={{ padding: '0.25rem 0.5rem' }}>{d.id}</td>
                        <td style={{ padding: '0.25rem 0.5rem' }}>{d.title}</td>
                        <td style={{ padding: '0.25rem 0.5rem' }}>{d.external_id}</td>
                        <td style={{ padding: '0.25rem 0.5rem' }}>{d.source_uri}</td>
                        <td style={{ padding: '0.25rem 0.5rem' }}>{d.status}</td>
                        <td style={{ padding: '0.25rem 0.5rem' }}>
                          <button
                            type="button"
                            onClick={() => void handleIndexDocument(d.id)}
                            style={{ marginRight: '0.5rem' }}
                          >
                            索引
                          </button>
                          <button type="button" onClick={() => void handleViewChunks(d.id)}>
                            {activeChunksDocId === d.id ? '收起 chunks' : '查看 chunks'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {activeChunksDocId && (
                <div
                  style={{
                    marginTop: '0.75rem',
                    padding: '0.5rem',
                    borderRadius: 4,
                    border: '1px dashed #ccc',
                    background: '#fafafa',
                  }}
                >
                  <h5>
                    文档 {activeChunksDocId} 的 chunks（最多显示 {chunks.length} 条）
                    {loadingChunks && <span style={{ marginLeft: '0.5rem' }}>加载中...</span>}
                  </h5>
                  {chunksError && <p style={{ color: 'red' }}>错误: {chunksError}</p>}
                  {!loadingChunks && chunks.length === 0 && <p>暂无 chunks 数据，请先尝试点击上方“索引”。</p>}
                  {chunks.length > 0 && (
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                      <thead>
                        <tr>
                          <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>#</th>
                          <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>section</th>
                          <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>text（前 80 字）</th>
                        </tr>
                      </thead>
                      <tbody>
                        {chunks.map((ch) => (
                          <tr key={ch.id}>
                            <td style={{ padding: '0.25rem 0.5rem' }}>{ch.chunk_index}</td>
                            <td style={{ padding: '0.25rem 0.5rem' }}>{ch.section_label || '-'}</td>
                            <td style={{ padding: '0.25rem 0.5rem' }}>
                              {ch.text.length > 80 ? `${ch.text.slice(0, 80)}...` : ch.text}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  )
}

export default KnowledgePage
