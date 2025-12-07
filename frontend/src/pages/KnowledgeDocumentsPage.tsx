import { useEffect, useState, type FormEvent } from 'react'
import {
  listCollections,
  listDocuments,
  createDocument,
  indexDocument,
  listChunks,
  deleteDocument,
  resetCollection,
  type KnowledgeCollection,
  type KnowledgeDocument,
  type KnowledgeChunk,
} from '../api/knowledge'

function KnowledgeDocumentsPage() {
  const [collections, setCollections] = useState<KnowledgeCollection[]>([])
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null)

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const [documentError, setDocumentError] = useState<string | null>(null)

  const [newDocTitle, setNewDocTitle] = useState('示例文档')
  const [newDocExternalId, setNewDocExternalId] = useState('')
  const [newDocSourceUri, setNewDocSourceUri] = useState('')

  const [activeChunksDocId, setActiveChunksDocId] = useState<number | null>(null)
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([])
  const [loadingChunks, setLoadingChunks] = useState(false)
  const [chunksError, setChunksError] = useState<string | null>(null)

  const loadCollections = async () => {
    try {
      const resp = await listCollections()
      setCollections(resp.items || [])
      if (!selectedCollectionId && resp.items && resp.items.length > 0) {
        setSelectedCollectionId(resp.items[0].id)
      }
    } catch (err) {
      // 文档页不专门显示集合错误
      console.error(err)
    }
  }

  const handleDeleteDocument = async (docId: number) => {
    if (!selectedCollectionId) return
    const ok = window.confirm(`确定要删除文档 ${docId} 及其所有 chunks 吗？此操作不可恢复。`)
    if (!ok) return
    setDocumentError(null)
    try {
      await deleteDocument(docId)
      // 若当前展开的 chunks 属于被删文档，则收起
      if (activeChunksDocId === docId) {
        setActiveChunksDocId(null)
        setChunks([])
        setChunksError(null)
      }
      await loadDocuments(selectedCollectionId)
    } catch (err) {
      setDocumentError((err as Error).message)
    }
  }

  const handleResetCollection = async () => {
    if (!selectedCollectionId) return
    const ok = window.confirm(
      `确定要清空集合 ${selectedCollectionId} 下的所有文档及 chunks 吗？此操作不可恢复。`,
    )
    if (!ok) return
    setDocumentError(null)
    try {
      await resetCollection(selectedCollectionId)
      setDocuments([])
      setActiveChunksDocId(null)
      setChunks([])
      setChunksError(null)
    } catch (err) {
      setDocumentError((err as Error).message)
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
      <h2>知识文档管理</h2>

      <section style={{ border: '1px solid #ddd', padding: '0.75rem', borderRadius: 4 }}>
        <h3>选择集合</h3>
        {collections.length === 0 && <p>暂无集合，请先在「知识集合」页面创建。</p>}
        {collections.length > 0 && (
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <select
              value={selectedCollectionId ?? ''}
              onChange={(e) =>
                setSelectedCollectionId(e.target.value ? Number(e.target.value) : null)
              }
            >
              {collections.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} - {c.name} ({c.domain})
                </option>
              ))}
            </select>
            {selectedCollectionId && (
              <button type="button" onClick={() => void handleResetCollection()}>
                清空当前集合数据
              </button>
            )}
          </div>
        )}
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
                            disabled={d.status === 'indexing'}
                          >
                            {d.status === 'indexing'
                              ? '索引中...'
                              : d.status === 'indexed'
                                ? '重新索引'
                                : d.status === 'error'
                                  ? '重新索引(上次失败)'
                                  : '索引'}
                          </button>
                          <button type="button" onClick={() => void handleViewChunks(d.id)}>
                            {activeChunksDocId === d.id ? '收起 chunks' : '查看 chunks'}
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDeleteDocument(d.id)}
                            style={{ marginLeft: '0.5rem', color: 'red' }}
                          >
                            删除
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

export default KnowledgeDocumentsPage
