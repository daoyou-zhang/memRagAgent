import { useEffect, useState, type FormEvent } from 'react'
import '../App.css'
import { createEpisodicJob, createSemanticJob, listJobs, runJob, type MemoryJob } from '../api/jobs'

function JobsPage() {
  const [formUserId, setFormUserId] = useState('u_123')
  const [formProjectId, setFormProjectId] = useState('proj_memRagAgent')
  const [formSessionId, setFormSessionId] = useState('sess_demo')
  const [formStartId, setFormStartId] = useState('1')
  const [formEndId, setFormEndId] = useState('100')

  const [formJobType, setFormJobType] = useState<'episodic' | 'semantic'>('episodic')

  const [jobs, setJobs] = useState<MemoryJob[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [filterStatus, setFilterStatus] = useState<string>('')
  const [filterSessionId, setFilterSessionId] = useState<string>('')

  const loadJobs = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listJobs({
        status: filterStatus || undefined,
        session_id: filterSessionId || undefined,
      })
      setJobs(data.items || [])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadJobs()
  }, [])

  const handleCreateJob = async (e: FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError(null)
    try {
      const startId = formStartId ? Number(formStartId) : undefined
      const endId = formEndId ? Number(formEndId) : undefined

      const payload = {
        user_id: formUserId || undefined,
        project_id: formProjectId || undefined,
        session_id: formSessionId,
        start_message_id: Number.isNaN(startId) ? undefined : startId,
        end_message_id: Number.isNaN(endId) ? undefined : endId,
      }

      if (formJobType === 'episodic') {
        await createEpisodicJob(payload)
      } else {
        await createSemanticJob(payload)
      }

      await loadJobs()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setCreating(false)
    }
  }

  const handleRunJob = async (jobId: number) => {
    setError(null)
    try {
      await runJob(jobId)
      await loadJobs()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div className="page-container">
      <section className="section-card">
        <h2 className="section-title">创建 Job（episodic / semantic）</h2>
        <form onSubmit={handleCreateJob} style={{ display: 'grid', gap: '0.5rem' }}>
          <div>
            <label>
              Job 类型:{' '}
              <select
                value={formJobType}
                onChange={(e) => setFormJobType(e.target.value as 'episodic' | 'semantic')}
              >
                <option value="episodic">episodic（会话总结）</option>
                <option value="semantic">semantic（画像记忆抽取）</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              用户 ID:{' '}
              <input value={formUserId} onChange={(e) => setFormUserId(e.target.value)} />
            </label>
          </div>
          <div>
            <label>
              项目 ID:{' '}
              <input
                value={formProjectId}
                onChange={(e) => setFormProjectId(e.target.value)}
              />
            </label>
          </div>
          <div>
            <label>
              会话 ID (session_id):{' '}
              <input
                value={formSessionId}
                onChange={(e) => setFormSessionId(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <div>
            <label>
              起始消息 ID (可选):{' '}
              <input
                value={formStartId}
                onChange={(e) => setFormStartId(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <div>
            <label>
              结束消息 ID (可选):{' '}
              <input
                value={formEndId}
                onChange={(e) => setFormEndId(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <button type="submit" disabled={creating}>
            {creating ? '创建中...' : '创建 Job'}
          </button>
          <p className="muted-text">
            说明：当前版本仅演示 Job 流水线，不会真正从消息表中读取内容，summary 由 LLM
            根据会话元信息生成占位性的总结文案。
          </p>
        </form>
      </section>

      <section className="section-card" style={{ marginTop: '1rem' }}>
        <h2 className="section-title">Job 列表</h2>
        <div
          style={{
            marginBottom: '0.5rem',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.5rem',
            alignItems: 'center',
          }}
        >
          <label>
            状态筛选:{' '}
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              style={{ minWidth: '8rem' }}
            >
              <option value="">全部</option>
              <option value="pending">pending</option>
              <option value="running">running</option>
              <option value="done">done</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label>
            会话 ID 筛选:{' '}
            <input
              value={filterSessionId}
              onChange={(e) => setFilterSessionId(e.target.value)}
              placeholder="留空表示全部会话"
              style={{ width: '16rem' }}
            />
          </label>
          <button type="button" onClick={() => void loadJobs()} disabled={loading}>
            {loading ? '刷新中...' : '按筛选条件刷新'}
          </button>
        </div>
        {error && <p style={{ color: 'red' }}>错误: {error}</p>}
        {jobs.length === 0 && <p>暂无 Job（或当前过滤条件下无结果）。</p>}
        {jobs.length > 0 && (
          <table className="results-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>用户</th>
                <th>项目</th>
                <th>会话 ID</th>
                <th>消息范围</th>
                <th>类型</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.id}</td>
                  <td>{job.user_id}</td>
                  <td>{job.project_id}</td>
                  <td>{job.session_id}</td>
                  <td>
                    {job.start_message_id ?? '-'} ~ {job.end_message_id ?? '-'}
                  </td>
                  <td>{job.job_type}</td>
                  <td>{job.status}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => void handleRunJob(job.id)}
                      disabled={job.status !== 'pending' && job.status !== 'failed'}
                    >
                      执行
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}

export default JobsPage
