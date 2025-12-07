import { useState, type FormEvent } from 'react'

interface Neo4jNode {
  identity: number | string
  labels?: string[]
  properties?: Record<string, any>
}

interface Neo4jRel {
  identity: number | string
  type: string
  start?: number | string
  end?: number | string
  properties?: Record<string, any>
}

interface GraphQueryRow {
  a?: Neo4jNode
  b?: Neo4jNode
  // Neo4j 变量长度关系（如 r*1..1）时，r 可能是单个关系或关系数组
  r?: Neo4jRel | Neo4jRel[]
}

interface GraphQueryResponse {
  result?: GraphQueryRow[]
  error?: string
}

function getNodeLabel(node?: Neo4jNode): string {
  if (!node) return ''
  const props = node.properties || {}
  return (
    (props.name as string) ||
    (props.title as string) ||
    (props.label as string) ||
    (props['名称'] as string) ||
    (node.labels && node.labels[0]) ||
    String(node.identity)
  )
}

function GraphPage() {
  // 关键字式查询：起点 / 关系 / 终点 / 深度
  const [startNode, setStartNode] = useState('')
  const [relationType, setRelationType] = useState('')
  const [endNode, setEndNode] = useState('')
  const [depth, setDepth] = useState(1)

  // 高级：直接写 Cypher
  const [cypher, setCypher] = useState(
    "MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50",
  )

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<GraphQueryRow[] | null>(null)

  const runQuery = async (finalCypher: string) => {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const resp = await fetch('/api/knowledge/graph/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cypher: finalCypher }),
      })
      const json = (await resp.json()) as GraphQueryResponse
      if (!resp.ok || json.error) {
        throw new Error(json.error || `HTTP ${resp.status}`)
      }
      setData(json.result || [])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const handleVisualSubmit = (e: FormEvent) => {
    e.preventDefault()

    const trimmedStart = startNode.trim()
    const trimmedRel = relationType.trim()
    const trimmedEnd = endNode.trim()
    const d = depth || 1

    let built = ''

    if (trimmedStart && trimmedEnd && trimmedRel) {
      built = `MATCH (a)-[r:${trimmedRel}]->(b) WHERE a.name CONTAINS '${trimmedStart}' AND b.name CONTAINS '${trimmedEnd}' RETURN a, r, b LIMIT 50`
    } else if (trimmedStart && trimmedRel) {
      built = `MATCH (a)-[r:${trimmedRel}]->(b) WHERE a.name CONTAINS '${trimmedStart}' RETURN a, r, b LIMIT 50`
    } else if (trimmedStart && trimmedEnd) {
      built = `MATCH (a)-[r*1..${d}]->(b) WHERE a.name CONTAINS '${trimmedStart}' AND b.name CONTAINS '${trimmedEnd}' RETURN a, r, b LIMIT 50`
    } else if (trimmedStart) {
      built = `MATCH (a)-[r*1..${d}]->(b) WHERE a.name CONTAINS '${trimmedStart}' RETURN a, r, b LIMIT 50`
    } else if (trimmedRel) {
      built = `MATCH (a)-[r:${trimmedRel}]->(b) RETURN a, r, b LIMIT 50`
    } else {
      // 如果什么都没填，就跑一个默认的小图
      built = 'MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50'
    }

    void runQuery(built)
  }

  const handleCypherSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!cypher.trim()) return
    void runQuery(cypher.trim())
  }

  const handleResetGraph = async () => {
    // 当前版本仅用于调试，保留接口但不在 UI 中暴露按钮
    void fetch('/api/knowledge/graph/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
  }

  const handleDeleteRelation = async (identity: string | number | undefined) => {
    if (identity === undefined || identity === null) return
    const ok = window.confirm(`确定要删除关系 ${String(identity)} 吗？此操作不可恢复。`)
    if (!ok) return
    setError(null)
    try {
      const resp = await fetch('/api/knowledge/graph/delete_relation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identity }),
      })
      const json = (await resp.json()) as { deleted?: number; error?: string }
      if (!resp.ok || json.error) {
        throw new Error(json.error || `HTTP ${resp.status}`)
      }
      // 为简单起见，这里不强制刷新查询结果，交给用户手动重新查询
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 1100, margin: '0 auto' }}>
      <h2>知识图谱查询实验台</h2>
      <p className="muted-text">
        上半部分提供关键字式查询（起点/关系/终点/深度），由前端拼装 Cypher；下半部分保留
        高级模式，可直接执行自定义 Cypher。当前结果先用表格查看结构是否正确，后续再接入
        可视化图谱。
      </p>

      {/* 关键字式查询 */}
      <form
        onSubmit={handleVisualSubmit}
        style={{ display: 'grid', gap: '0.5rem', marginTop: '0.75rem', marginBottom: '1rem' }}
      >
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <label style={{ flex: '1 1 180px' }}>
            起点（name 包含）:
            <input
              value={startNode}
              onChange={(e) => setStartNode(e.target.value)}
              style={{ width: '100%' }}
              placeholder="如：甲木、张三、事业节点..."
            />
          </label>
          <label style={{ flex: '1 1 160px' }}>
            关系类型:
            <input
              value={relationType}
              onChange={(e) => setRelationType(e.target.value)}
              style={{ width: '100%' }}
              placeholder="如：APPLIES、BELONGS_TO"
            />
          </label>
          <label style={{ flex: '1 1 180px' }}>
            终点（name 包含）:
            <input
              value={endNode}
              onChange={(e) => setEndNode(e.target.value)}
              style={{ width: '100%' }}
              placeholder="可留空"
            />
          </label>
          <label style={{ flex: '0 0 120px' }}>
            深度:
            <input
              type="number"
              min={1}
              max={5}
              value={depth}
              onChange={(e) =>
                setDepth(Number.isNaN(Number(e.target.value)) ? 1 : Number(e.target.value))
              }
              style={{ width: '100%' }}
            />
          </label>
        </div>
        <button type="submit" disabled={loading}>
          {loading ? '查询中...' : '执行关键字查询'}
        </button>
      </form>

      {/* 高级：自定义 Cypher */}
      <form
        onSubmit={handleCypherSubmit}
        style={{ display: 'grid', gap: '0.5rem', marginBottom: '1rem' }}
      >
        <label>
          高级 Cypher（可选）:
          <br />
          <textarea
            value={cypher}
            onChange={(e) => setCypher(e.target.value)}
            rows={3}
            style={{ width: '100%', fontFamily: 'monospace' }}
          />
        </label>
        <button type="submit" disabled={loading || !cypher.trim()}>
          {loading ? '查询中...' : '执行自定义 Cypher'}
        </button>
      </form>

      {error && (
        <p style={{ color: 'red', marginTop: '0.5rem' }}>错误: {error}</p>
      )}

      {data && (
        <div style={{ marginTop: '1rem' }}>
          <h3>查询结果</h3>
          {data.length === 0 && <p>暂无结果。</p>}
          {data.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>#</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>a 节点</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>关系 r</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>b 节点</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{idx + 1}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>
                      {row.a && (
                        <>
                          <div>{getNodeLabel(row.a)}</div>
                          <div className="muted-text">
                            id={String(row.a.identity)} labels={row.a.labels?.join(', ')}
                          </div>
                        </>
                      )}
                    </td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>
                      {row.r && (() => {
                        const rel = Array.isArray(row.r) ? row.r[0] : row.r
                        if (!rel) return null
                        return (
                          <>
                            <div>{rel.type}</div>
                            <div className="muted-text">
                              id={String(rel.identity)}
                            </div>
                            <button
                              type="button"
                              style={{ marginTop: '0.25rem', fontSize: 11, color: 'red' }}
                              onClick={() => void handleDeleteRelation(rel.identity)}
                            >
                              删除关系
                            </button>
                          </>
                        )
                      })()}
                    </td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>
                      {row.b && (
                        <>
                          <div>{getNodeLabel(row.b)}</div>
                          <div className="muted-text">
                            id={String(row.b.identity)} labels={row.b.labels?.join(', ')}
                          </div>
                        </>
                      )}
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

export default GraphPage
