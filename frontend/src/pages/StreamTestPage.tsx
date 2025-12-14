import { useRef, useState } from 'react'
import { DAOYOU_BASE } from '../api/cognitive'

function StreamTestPage() {
  const [input, setInput] = useState('你好，介绍一下你自己')
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle')
  const [timeText, setTimeText] = useState('耗时: -')
  const [chunkText, setChunkText] = useState('片段: 0')
  const [intentBlocks, setIntentBlocks] = useState<string[]>([])
  const [toolBlocks, setToolBlocks] = useState<string[]>([])
  const [contentText, setContentText] = useState('')
  const [doneBlocks, setDoneBlocks] = useState<string[]>([])
  const [errorBlocks, setErrorBlocks] = useState<string[]>([])

  const startTimeRef = useRef<number | null>(null)
  const chunkCountRef = useRef(0)

  const presets = [
    { label: '👋 打招呼', text: '你好，介绍一下你自己' },
    { label: '🔮 八字排盘', text: '帮我排一下八字，1990年6月25日4点30分出生，男，北京' },
    { label: '📝 写诗', text: '写一首关于春天的诗' },
    { label: '🤖 技术问答', text: '解释一下什么是机器学习' },
  ] as const

  const resetOutput = () => {
    setIntentBlocks([])
    setToolBlocks([])
    setContentText('')
    setDoneBlocks([])
    setErrorBlocks([])
    setStatus('idle')
    setTimeText('耗时: -')
    setChunkText('片段: 0')
    startTimeRef.current = null
    chunkCountRef.current = 0
  }

  const updateStats = () => {
    if (!startTimeRef.current) return
    const elapsed = ((Date.now() - startTimeRef.current) / 1000).toFixed(1)
    setTimeText(`耗时: ${elapsed}s`)
    setChunkText(`片段: ${chunkCountRef.current}`)
  }

  const handleStream = async () => {
    const trimmed = input.trim()
    if (!trimmed) {
      alert('请输入内容')
      return
    }

    resetOutput()
    setStatus('connecting')
    startTimeRef.current = Date.now()

    try {
      const response = await fetch(`${DAOYOU_BASE}/api/v1/cognitive/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: trimmed,
          stream: true,
          user_id: 'admin',
          project_id: '',
        }),
      })

      setStatus('connected')

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('浏览器不支持流式读取')
      }

      const decoder = new TextDecoder()
      let done = false

      while (!done) {
        const { done: streamDone, value } = await reader.read()
        if (streamDone) break
        const text = decoder.decode(value)
        const lines = text.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.substring(6)) as any
            chunkCountRef.current += 1

            if (data.category) {
              setIntentBlocks(prev => [
                ...prev,
                `🎯 意图: ${data.category} (置信度: ${(data.confidence * 100).toFixed(0)}%)`,
              ])
            } else if (data.tool_name) {
              setToolBlocks(prev => [
                ...prev,
                `🔧 工具: ${data.tool_name} (${data.success ? '成功' : '失败'})`,
              ])
            } else if (data.text) {
              setContentText(prev => prev + data.text)
            } else if (data.session_id) {
              setDoneBlocks(prev => [
                ...prev,
                `✅ 完成 (耗时: ${data.processing_time.toFixed(2)}s)`,
              ])
            } else if (data.error) {
              setErrorBlocks(prev => [
                ...prev,
                `❌ 错误: ${data.error}`,
              ])
            }

            updateStats()
          } catch (e) {
            // 忽略单条解析错误
          }
        }
      }
    } catch (err: any) {
      setStatus('error')
      setErrorBlocks(prev => [
        ...prev,
        `❌ 请求失败: ${err?.message || String(err)}`,
      ])
    }
  }

  const handleNormal = async () => {
    const trimmed = input.trim()
    if (!trimmed) {
      alert('请输入内容')
      return
    }

    resetOutput()
    setStatus('connecting')
    startTimeRef.current = Date.now()

    try {
      const resp = await fetch(`${DAOYOU_BASE}/api/v1/cognitive/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: trimmed,
          stream: false,
          user_id: 'test_user',
          project_id: 'test_project',
        }),
      })

      const data: any = await resp.json()
      const elapsed = ((Date.now() - (startTimeRef.current ?? Date.now())) / 1000).toFixed(2)

      setStatus('connected')
      setIntentBlocks([
        `🎯 意图: ${data.intent?.category || '-'} (置信度: ${((data.intent?.confidence || 0) * 100).toFixed(0)}%)`,
      ])
      if (data.tool_used) {
        setToolBlocks([`🔧 工具: ${data.tool_used}`])
      }
      setContentText(data.content || '无内容')
      setDoneBlocks([`✅ 完成 (耗时: ${elapsed}s)`])

      setTimeText(`耗时: ${elapsed}s`)
      setChunkText('片段: 1 (完整响应)')
    } catch (err: any) {
      setStatus('error')
      setErrorBlocks([`❌ 请求失败: ${err?.message || String(err)}`])
    }
  }

  const statusDotStyle: React.CSSProperties = {
    width: 10,
    height: 10,
    borderRadius: '50%',
    background: '#ccc',
    flexShrink: 0,
  }

  if (status === 'connecting') {
    statusDotStyle.background = '#ffa502'
  } else if (status === 'connected') {
    statusDotStyle.background = '#2ed573'
  } else if (status === 'error') {
    statusDotStyle.background = '#ff4757'
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 960, margin: '0 auto' }}>
      <h2 style={{ marginBottom: '1rem' }}>🚀 流式响应测试</h2>

      <div
        style={{
          background: '#ffffff10',
          borderRadius: 16,
          padding: 16,
          marginBottom: 16,
          border: '1px solid var(--border-color, #333)',
        }}
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 8, fontWeight: 600 }}>快速测试</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {presets.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => setInput(p.text)}
                style={{
                  padding: '4px 10px',
                  borderRadius: 20,
                  border: '1px solid #444',
                  background: '#1e1e1e',
                  color: '#eee',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>
            输入内容
          </label>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={4}
            placeholder="请输入你的问题..."
            style={{
              width: '100%',
              padding: 8,
              borderRadius: 8,
              border: '1px solid #555',
              background: '#111',
              color: '#eee',
              resize: 'vertical',
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={handleStream}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: 'none',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            🌊 流式请求
          </button>
          <button
            type="button"
            onClick={handleNormal}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: '1px solid #555',
              background: '#222',
              color: '#eee',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            📦 普通请求
          </button>
          <button
            type="button"
            onClick={resetOutput}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: 'none',
              background: '#ff4757',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            🗑️ 清空
          </button>
        </div>
      </div>

      <div
        style={{
          background: '#111',
          borderRadius: 16,
          padding: 16,
          border: '1px solid var(--border-color, #333)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <div style={statusDotStyle} />
          <span style={{ fontWeight: 600 }}>响应输出</span>
        </div>

        <div
          style={{
            background: '#1a1a2e',
            borderRadius: 8,
            padding: 12,
            minHeight: 160,
            maxHeight: 360,
            overflowY: 'auto',
            fontFamily: 'Menlo, Monaco, Consolas, monospace',
            fontSize: 14,
            lineHeight: 1.6,
            color: '#eee',
          }}
        >
          {intentBlocks.length === 0 &&
            toolBlocks.length === 0 &&
            !contentText &&
            doneBlocks.length === 0 &&
            errorBlocks.length === 0 && (
              <span style={{ color: '#666' }}>等待请求...</span>
          )}

          {intentBlocks.map((t, i) => (
            <div
              key={`intent-${i}`}
              style={{
                marginBottom: 8,
                padding: 8,
                borderRadius: 4,
                background: 'rgba(255, 217, 61, 0.1)',
                color: '#ffd93d',
              }}
            >
              {t}
            </div>
          ))}

          {toolBlocks.map((t, i) => (
            <div
              key={`tool-${i}`}
              style={{
                marginBottom: 8,
                padding: 8,
                borderRadius: 4,
                background: 'rgba(107, 203, 119, 0.1)',
                color: '#6bcb77',
              }}
            >
              {t}
            </div>
          ))}

          {contentText && (
            <div style={{ color: '#fff', whiteSpace: 'pre-wrap' }}>{contentText}</div>
          )}

          {doneBlocks.map((t, i) => (
            <div
              key={`done-${i}`}
              style={{
                marginTop: 8,
                padding: 8,
                borderRadius: 4,
                background: 'rgba(77, 150, 255, 0.1)',
                color: '#4d96ff',
              }}
            >
              {t}
            </div>
          ))}

          {errorBlocks.map((t, i) => (
            <div
              key={`err-${i}`}
              style={{
                marginTop: 8,
                padding: 8,
                borderRadius: 4,
                background: 'rgba(255, 107, 107, 0.1)',
                color: '#ff6b6b',
              }}
            >
              {t}
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 14, color: '#ccc' }}>
          <span
            style={{
              background: '#222',
              padding: '4px 10px',
              borderRadius: 4,
            }}
          >
            {timeText}
          </span>
          <span
            style={{
              background: '#222',
              padding: '4px 10px',
              borderRadius: 4,
            }}
          >
            {chunkText}
          </span>
        </div>
      </div>
    </div>
  )
}

export default StreamTestPage
