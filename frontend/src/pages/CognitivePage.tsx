import { useState, type FormEvent } from 'react'
import {
  cognitiveProcess,
  type CognitiveRequest,
  type CognitiveResponse,
} from '../api/cognitive'

function CognitivePage() {
  // 表单字段
  const [input, setInput] = useState('')
  const [userId, setUserId] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [enableMemory, setEnableMemory] = useState(true)
  const [memoryDepth, setMemoryDepth] = useState(5)
  const [ragLevel, setRagLevel] = useState(3)
  const [enableLearning, setEnableLearning] = useState(true)
  const [qualityLevel, setQualityLevel] = useState<'fast' | 'balanced' | 'high'>('balanced')

  // 自定义 Prompt（可选）
  const [showPrompts, setShowPrompts] = useState(false)
  const [intentSystemPrompt, setIntentSystemPrompt] = useState('')
  const [responseSystemPrompt, setResponseSystemPrompt] = useState('')

  // 请求状态
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CognitiveResponse | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim()) {
      setError('请输入内容')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    const req: CognitiveRequest = {
      input: input.trim(),
      user_id: userId || undefined,
      session_id: sessionId || undefined,
      project_id: projectId || undefined,
      enable_memory: enableMemory,
      memory_depth: memoryDepth,
      rag_level: ragLevel,
      enable_learning: enableLearning,
      quality_level: qualityLevel,
      intent_system_prompt: intentSystemPrompt || undefined,
      response_system_prompt: responseSystemPrompt || undefined,
    }

    try {
      const data = await cognitiveProcess(req)
      setResult(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 1000, margin: '0 auto' }}>
      <h2>🧠 道友认知测试台</h2>
      <p style={{ color: 'var(--text-secondary, #888)', marginBottom: '1rem' }}>
        测试 daoyou_agent 的认知 API（端口 8000）
      </p>

      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.75rem' }}>
        {/* 主要输入 */}
        <div>
          <label style={{ fontWeight: 'bold' }}>
            输入内容 *
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={3}
              placeholder="你好，道友"
              style={{ width: '100%', marginTop: '0.25rem' }}
            />
          </label>
        </div>

        {/* ID 字段 */}
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <label>
            User ID:
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              style={{ marginLeft: '0.5rem', width: '120px' }}
            />
          </label>
          <label>
            Session ID:
            <input
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              style={{ marginLeft: '0.5rem', width: '120px' }}
            />
          </label>
          <label>
            Project ID:
            <input
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              style={{ marginLeft: '0.5rem', width: '120px' }}
            />
          </label>
        </div>

        {/* 开关选项 */}
        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
          <label>
            <input
              type="checkbox"
              checked={enableMemory}
              onChange={(e) => setEnableMemory(e.target.checked)}
            />
            {' '}启用记忆
          </label>
          <label>
            <input
              type="checkbox"
              checked={enableLearning}
              onChange={(e) => setEnableLearning(e.target.checked)}
            />
            {' '}启用学习
          </label>
        </div>

        {/* 数值参数 */}
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <label>
            记忆深度:
            <input
              type="number"
              min={1}
              max={50}
              value={memoryDepth}
              onChange={(e) => setMemoryDepth(Number(e.target.value) || 5)}
              style={{ marginLeft: '0.5rem', width: '60px' }}
            />
          </label>
          <label>
            RAG 级别:
            <input
              type="number"
              min={0}
              max={5}
              value={ragLevel}
              onChange={(e) => setRagLevel(Number(e.target.value) || 0)}
              style={{ marginLeft: '0.5rem', width: '60px' }}
            />
          </label>
          <label>
            质量级别:
            <select
              value={qualityLevel}
              onChange={(e) => setQualityLevel(e.target.value as 'fast' | 'balanced' | 'high')}
              style={{ marginLeft: '0.5rem' }}
            >
              <option value="fast">快速</option>
              <option value="balanced">平衡</option>
              <option value="high">高质量</option>
            </select>
          </label>
        </div>

        {/* 自定义 Prompt */}
        <div>
          <button
            type="button"
            onClick={() => setShowPrompts(!showPrompts)}
            style={{ background: 'none', border: 'none', color: 'var(--text-secondary, #888)', cursor: 'pointer', padding: 0 }}
          >
            {showPrompts ? '▼' : '▶'} 自定义 Prompt（可选）
          </button>
          {showPrompts && (
            <div style={{ marginTop: '0.5rem', display: 'grid', gap: '0.5rem' }}>
              <label>
                意图理解 System Prompt:
                <textarea
                  value={intentSystemPrompt}
                  onChange={(e) => setIntentSystemPrompt(e.target.value)}
                  rows={3}
                  placeholder="留空使用默认值"
                  style={{ width: '100%', marginTop: '0.25rem', fontSize: '0.9rem' }}
                />
              </label>
              <label>
                回复生成 System Prompt:
                <textarea
                  value={responseSystemPrompt}
                  onChange={(e) => setResponseSystemPrompt(e.target.value)}
                  rows={3}
                  placeholder="留空使用默认值"
                  style={{ width: '100%', marginTop: '0.25rem', fontSize: '0.9rem' }}
                />
              </label>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: '0.5rem 1.5rem',
            fontSize: '1rem',
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? '处理中...' : '发送请求'}
        </button>
      </form>

      {/* 错误提示 */}
      {error && (
        <div
          style={{
            marginTop: '1rem',
            padding: '0.75rem',
            background: 'var(--error-bg, #4a1f1f)',
            border: '1px solid var(--error-border, #8b3030)',
            borderRadius: '4px',
            color: 'var(--error-text, #ff6b6b)',
          }}
        >
          {error}
        </div>
      )}

      {/* 结果展示 */}
      {result && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3>📝 回复内容</h3>
          <div
            style={{
              padding: '1rem',
              background: 'var(--bg-secondary, #2a2a2a)',
              borderRadius: '8px',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6,
              color: 'var(--text-primary, #e0e0e0)',
            }}
          >
            {result.content}
          </div>

          <h3 style={{ marginTop: '1rem' }}>🎯 意图分析</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              <tr>
                <td style={tdStyle}>意图类别</td>
                <td style={tdStyle}>
                  <span style={{ 
                    background: 'var(--accent-bg, #1e3a5f)', 
                    padding: '2px 8px', 
                    borderRadius: '4px',
                    fontWeight: 'bold'
                  }}>
                    {result.intent?.category || '-'}
                  </span>
                </td>
              </tr>
              <tr>
                <td style={tdStyle}>置信度</td>
                <td style={tdStyle}>{(result.intent?.confidence ?? result.confidence)?.toFixed(2) || '-'}</td>
              </tr>
              <tr>
                <td style={tdStyle}>意图摘要</td>
                <td style={tdStyle}>{result.intent?.summary || '-'}</td>
              </tr>
              <tr>
                <td style={tdStyle}>需要工具</td>
                <td style={tdStyle}>
                  {result.intent?.needs_tool ? (
                    <span style={{ color: 'var(--warning-text, #ffb74d)' }}>是</span>
                  ) : (
                    <span style={{ color: 'var(--text-muted, #666)' }}>否</span>
                  )}
                </td>
              </tr>
              {result.intent?.suggested_tools && result.intent.suggested_tools.length > 0 && (
                <tr>
                  <td style={tdStyle}>建议工具</td>
                  <td style={tdStyle}>{result.intent.suggested_tools.join(', ')}</td>
                </tr>
              )}
              {result.intent?.entities && result.intent.entities.length > 0 && (
                <tr>
                  <td style={tdStyle}>识别实体</td>
                  <td style={tdStyle}>
                    {result.intent.entities.map((e, i) => (
                      <span key={i} style={{ 
                        background: 'var(--tag-bg, #3d2e1f)', 
                        padding: '2px 6px', 
                        borderRadius: '3px',
                        marginRight: '4px',
                        fontSize: '0.9rem'
                      }}>
                        {String(e.type)}: {String(e.value)}
                      </span>
                    ))}
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <h3 style={{ marginTop: '1rem' }}>📊 处理信息</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              <tr>
                <td style={tdStyle}>处理时间</td>
                <td style={tdStyle}>{result.processing_time?.toFixed(3)}s</td>
              </tr>
              <tr>
                <td style={tdStyle}>AI 服务</td>
                <td style={tdStyle}>{result.ai_service_used || '-'}</td>
              </tr>
              <tr>
                <td style={tdStyle}>Session ID</td>
                <td style={tdStyle}>{result.session_id || '-'}</td>
              </tr>
              <tr>
                <td style={tdStyle}>User ID</td>
                <td style={tdStyle}>{result.user_id || '-'}</td>
              </tr>
            </tbody>
          </table>

          <details style={{ marginTop: '1rem' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>
              查看完整 JSON 响应
            </summary>
            <pre
              style={{
                marginTop: '0.5rem',
                padding: '0.75rem',
                background: '#282c34',
                color: '#abb2bf',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '0.85rem',
              }}
            >
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  )
}

const tdStyle: React.CSSProperties = {
  padding: '0.5rem',
  border: '1px solid var(--border-color, #404040)',
}

export default CognitivePage
