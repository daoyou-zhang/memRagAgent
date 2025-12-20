import { useState } from 'react'
import './App.css'

interface ApiTestCaseResult {
  case_name: string
  success: boolean
  status_code?: number | null
  response_time_ms?: number | null
  error?: string | null
  failed_validations: string[]
}

interface ApiTestExecutionResult {
  success_rate: number
  total_cases: number
  passed_cases: number
  failed_cases: number
  case_results: ApiTestCaseResult[]
}

interface ApiTestRecord {
  id: string
  target: string
  status: string
  success_rate?: number | null
  total_checks?: number | null
  passed_checks?: number | null
  api_result?: ApiTestExecutionResult | null
}

interface RunApiTestResponse {
  record: ApiTestRecord
}

type TabId = 'overview' | 'api' | 'ui' | 'history'

function App() {
  const [target, setTarget] = useState('')
  const [requirements, setRequirements] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RunApiTestResponse | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  const handleRunApiTest = async () => {
    if (!target || !requirements) {
      setError('请先填写目标地址和测试需求')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const resp = await fetch('http://127.0.0.1:8010/autotest/run-api-test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target,
          requirements,
          base_url: baseUrl || null,
        }),
      })

      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(`HTTP ${resp.status}: ${text}`)
      }

      const data: RunApiTestResponse = await resp.json()
      setResult(data)
    } catch (e) {
      const message = e instanceof Error ? e.message : '调用失败'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-root">
      <header className="app-header">
        <div>
          <h1>Autotest 测试工程</h1>
          <p className="app-subtitle">基于大模型的自动化测试工作台（API / UI / 连通性）</p>
        </div>
      </header>

      <main className="app-main">
        <div className="app-main-inner">
          <nav className="app-nav">
            <button
              type="button"
              className={`app-nav-tab ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              概览
            </button>
            <button
              type="button"
              className={`app-nav-tab ${activeTab === 'api' ? 'active' : ''}`}
              onClick={() => setActiveTab('api')}
            >
              API 测试
            </button>
            <button
              type="button"
              className={`app-nav-tab ${activeTab === 'ui' ? 'active' : ''}`}
              onClick={() => setActiveTab('ui')}
            >
              UI 测试
            </button>
            <button
              type="button"
              className={`app-nav-tab ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              测试历史
            </button>
          </nav>

          {activeTab === 'overview' && (
            <>
              <section className="app-section">
                <h2>快速入口</h2>
                <div className="grid">
                  <div className="card primary">
                    <h3>API 测试</h3>
                    <p>针对后端接口自动生成测试用例，执行并校验响应状态码与字段。</p>
                    <button
                      className="card-button"
                      type="button"
                      onClick={() => setActiveTab('api')}
                    >
                      打开 API 测试台
                    </button>
                  </div>

                  <div className="card">
                    <h3>UI 测试（即将支持）</h3>
                    <p>基于 Playwright 的关键路径 UI 自动化测试，覆盖核心用户流程。</p>
                    <button className="card-button ghost" type="button" disabled>
                      敬请期待
                    </button>
                  </div>

                  <div className="card">
                    <h3>连通性检查</h3>
                    <p>对服务健康度、依赖链路和基础网络连通性进行自动巡检。</p>
                    <button
                      className="card-button"
                      type="button"
                      onClick={() => console.log('TODO: 跳转到连通性检查页面')}
                    >
                      运行一次健康检查
                    </button>
                  </div>

                  <div className="card">
                    <h3>测试历史</h3>
                    <p>查看最近的测试记录、成功率趋势以及关键问题摘要。</p>
                    <button
                      className="card-button"
                      type="button"
                      onClick={() => setActiveTab('history')}
                    >
                      查看测试记录
                    </button>
                  </div>
                </div>
              </section>

              <section className="app-section">
                <h2>当前状态</h2>
                <div className="status-panel">
                  <div className="status-item">
                    <span className="status-label">LLM 规划器</span>
                    <span className="status-value">本地 daoyou_agent</span>
                  </div>
                  <div className="status-item">
                    <span className="status-label">结果存储</span>
                    <span className="status-value">内存仓库（开发模式）</span>
                  </div>
                  <div className="status-item">
                    <span className="status-label">前端工程</span>
                    <span className="status-value">testfrontend (Vite + React + TS)</span>
                  </div>
                </div>
              </section>
            </>
          )}

          {activeTab === 'api' && (
            <section className="app-section api-section">
              <h2>API 测试控制台</h2>
              <div className="api-form">
            <div className="api-form-row">
              <label className="api-label">
                目标地址
                <input
                  className="api-input"
                  placeholder="例如：http://127.0.0.1:8000/health"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                />
              </label>
            </div>
            <div className="api-form-row">
              <label className="api-label">
                测试需求
                <textarea
                  className="api-textarea"
                  placeholder="用自然语言描述你希望验证的行为，例如：检查返回 200 且 JSON 中包含 code 字段。"
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  rows={3}
                />
              </label>
            </div>
            <div className="api-form-row api-form-row-inline">
              <label className="api-label">
                基础 URL（可选）
                <input
                  className="api-input"
                  placeholder="例如：http://127.0.0.1:8000"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="card-button"
                onClick={handleRunApiTest}
                disabled={loading}
              >
                {loading ? '运行中…' : '运行一次 API 测试'}
              </button>
            </div>
          </div>
          {error && <div className="api-error">{error}</div>}
          {result && (
            <div className="api-result">
              <div className="api-result-header">
                <span className="api-result-target">{result.record.target}</span>
                <span
                  className={`badge-status badge-${result.record.status.toLowerCase()}`}
                >
                  {result.record.status}
                </span>
              </div>
              <div className="api-result-metrics">
                <span>
                  成功率：
                  {result.record.success_rate != null
                    ? `${result.record.success_rate.toFixed(1)}%`
                    : '—'}
                </span>
                <span>
                  用例：
                  {result.record.api_result?.passed_cases ?? result.record.passed_checks ?? 0}
                  /
                  {result.record.api_result?.total_cases ?? result.record.total_checks ?? 0}
                </span>
              </div>

              {result.record.api_result && (
                <div className="api-cases">
                  {result.record.api_result.case_results.map((c, idx) => (
                    <div
                      key={idx}
                      className={`api-case ${c.success ? 'api-case-success' : 'api-case-failed'}`}
                    >
                      <div className="api-case-header">
                        <span className="api-case-name">{c.case_name}</span>
                        <span
                          className={`badge-status ${
                            c.success ? 'badge-success' : 'badge-failed'
                          }`}
                        >
                          {c.success ? 'PASS' : 'FAIL'}
                        </span>
                      </div>
                      <div className="api-case-meta">
                        <span>状态码：{c.status_code ?? '—'}</span>
                        <span>
                          耗时：
                          {c.response_time_ms != null
                            ? `${c.response_time_ms.toFixed(1)} ms`
                            : '—'}
                        </span>
                      </div>
                      {c.error && <div className="api-case-error">错误：{c.error}</div>}
                      {c.failed_validations && c.failed_validations.length > 0 && (
                        <ul className="api-case-validations">
                          {c.failed_validations.map((fv, i) => (
                            <li key={i}>{fv}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
          )}

          {activeTab === 'ui' && (
            <section className="app-section">
              <h2>UI 测试</h2>
              <p>后续将接入 Playwright，支持关键路径 UI 自动化测试。</p>
            </section>
          )}

          {activeTab === 'history' && (
            <section className="app-section">
              <h2>测试历史</h2>
              <p>后续会在这里展示最近的测试记录和成功率趋势。</p>
            </section>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <span>Autotest · 基于 LLM 的自驱动测试实验工程</span>
      </footer>
    </div>
  )
}

export default App
