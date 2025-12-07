import { useEffect, useState, type FormEvent } from 'react'
import '../App.css'
import {
  createEpisodicJob,
  createSemanticJob,
  createProfileJob,
  listJobs,
  runJob,
  closeSession,
  createProfileJobAuto,
  type MemoryJob,
  cleanupJobs,
} from '../api/jobs'

function JobsPage() {
  const [formUserId, setFormUserId] = useState('48eedcd8-ed89-464c-8109-7bcb6fe94e36')
  const [formProjectId, setFormProjectId] = useState('DAOYOUTEST')
  const [formSessionId, setFormSessionId] = useState('')
  const [formStartId, setFormStartId] = useState('1')
  const [formEndId, setFormEndId] = useState('100')

  const [formJobType, setFormJobType] = useState<'episodic' | 'semantic' | 'profile'>('episodic')

  const [jobs, setJobs] = useState<MemoryJob[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [filterStatus, setFilterStatus] = useState<string>('')
  const [filterSessionId, setFilterSessionId] = useState<string>('')

  const [closeSessionId, setCloseSessionId] = useState('')
  const [closeSessionResult, setCloseSessionResult] = useState<string>('')

  const [autoProfileUserId, setAutoProfileUserId] = useState(formUserId)
  const [autoProfileProjectId, setAutoProfileProjectId] = useState(formProjectId)
  const [autoProfileResult, setAutoProfileResult] = useState<string>('')

  const [cleanupStatus, setCleanupStatus] = useState<string>('done,failed')
  const [cleanupUserId, setCleanupUserId] = useState('')
  const [cleanupProjectId, setCleanupProjectId] = useState('')
  const [cleanupBefore, setCleanupBefore] = useState('')
  const [cleanupResult, setCleanupResult] = useState<string>('')

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
      } else if (formJobType === 'semantic') {
        await createSemanticJob(payload)
      } else {
        // profile_aggregate Job 只需要 user_id / project_id
        await createProfileJob({ user_id: payload.user_id, project_id: payload.project_id })
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
      <section className="section-card" style={{ marginBottom: '1rem' }}>
        <h2 className="section-title">会话关闭 & 画像自动 Job 调度（后端自动逻辑入口）</h2>
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <div>
            <h3 style={{ margin: 0, marginBottom: '0.25rem', fontSize: '0.95rem' }}>关闭会话并按 auto_* 开关自动创建 Job</h3>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <label>
                session_id:{' '}
                <input
                  value={closeSessionId}
                  onChange={(e) => setCloseSessionId(e.target.value)}
                  style={{ minWidth: '14rem' }}
                  placeholder="与后端 conversation_sessions.session_id 一致"
                />
              </label>
              <button
                type="button"
                onClick={async () => {
                  setError(null)
                  setCloseSessionResult('')
                  if (!closeSessionId) {
                    setCloseSessionResult('请先填写 session_id')
                    return
                  }
                  try {
                    const resp = await closeSession(closeSessionId)
                    setCloseSessionResult(
                      `status=${resp.status}, messages=${resp.message_count}, created_jobs=${resp.created_jobs.length}`,
                    )
                    await loadJobs()
                  } catch (err) {
                    const msg = (err as Error).message
                    setError(msg)
                    setCloseSessionResult(`调用失败: ${msg}`)
                  }
                }}
              >
                关闭会话并根据 auto_* 创建 Job
              </button>
            </div>
            {closeSessionResult && (
              <p className="muted-text" style={{ marginTop: '0.25rem' }}>
                {closeSessionResult}
              </p>
            )}
          </div>

          <div>
            <h3 style={{ margin: 0, marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              按 semantic 增量触发画像 Job（/jobs/profile/auto）
            </h3>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <label>
                user_id:{' '}
                <input
                  value={autoProfileUserId}
                  onChange={(e) => setAutoProfileUserId(e.target.value)}
                  style={{ minWidth: '10rem' }}
                />
              </label>
              <label>
                project_id:{' '}
                <input
                  value={autoProfileProjectId}
                  onChange={(e) => setAutoProfileProjectId(e.target.value)}
                  style={{ minWidth: '10rem' }}
                />
              </label>
              <button
                type="button"
                onClick={async () => {
                  setError(null)
                  setAutoProfileResult('')
                  if (!autoProfileUserId) {
                    setAutoProfileResult('请先填写 user_id')
                    return
                  }
                  try {
                    const resp = await createProfileJobAuto({
                      user_id: autoProfileUserId,
                      project_id: autoProfileProjectId || undefined,
                    })
                    setAutoProfileResult(
                      `status=${resp.status}, new_semantic=${resp.new_semantic_count}, min=${resp.min_new_semantic}`,
                    )
                    await loadJobs()
                  } catch (err) {
                    const msg = (err as Error).message
                    setError(msg)
                    setAutoProfileResult(`调用失败: ${msg}`)
                  }
                }}
              >
                检查并按增量创建 profile Job
              </button>
            </div>
            {autoProfileResult && (
              <p className="muted-text" style={{ marginTop: '0.25rem' }}>
                {autoProfileResult}
              </p>
            )}
          </div>
        </div>
      </section>
      <section className="section-card">
        <h2 className="section-title">创建 Job（episodic / semantic）</h2>
        <form onSubmit={handleCreateJob} style={{ display: 'grid', gap: '0.5rem' }}>
          <div>
            <label>
              Job 类型:{' '}
              <select
                value={formJobType}
                onChange={(e) => setFormJobType(e.target.value as 'episodic' | 'semantic' | 'profile')}
              >
                <option value="episodic">episodic（会话总结）</option>
                <option value="semantic">semantic（画像记忆抽取）</option>
                <option value="profile">profile（画像聚合刷新）</option>
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
        <h2 className="section-title">Job 清理</h2>
        <div style={{ display: 'grid', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <p className="muted-text" style={{ marginBottom: 0 }}>
            按条件删除旧的 Job 记录（默认只清理 done,failed）。时间按北京时间填写。
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            <label>
              status 列表(逗号分隔):{' '}
              <input
                value={cleanupStatus}
                onChange={(e) => setCleanupStatus(e.target.value)}
                style={{ width: '12rem' }}
              />
            </label>
            <label>
              user_id:{' '}
              <input
                value={cleanupUserId}
                onChange={(e) => setCleanupUserId(e.target.value)}
                style={{ width: '10rem' }}
              />
            </label>
            <label>
              project_id:{' '}
              <input
                value={cleanupProjectId}
                onChange={(e) => setCleanupProjectId(e.target.value)}
                style={{ width: '10rem' }}
              />
            </label>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            <label>
              删除此时间之前的 Job (updated_at, 北京时间):{' '}
              <input
                value={cleanupBefore}
                onChange={(e) => setCleanupBefore(e.target.value)}
                style={{ width: '20rem' }}
                placeholder="例如 2024-01-01T00:00:00"
              />
            </label>
            <button
              type="button"
              onClick={async () => {
                setError(null)
                setCleanupResult('')
                try {
                  const statusArr = cleanupStatus
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean)
                  const resp = await cleanupJobs({
                    status: statusArr.length ? statusArr : undefined,
                    user_id: cleanupUserId || undefined,
                    project_id: cleanupProjectId || undefined,
                    before: cleanupBefore || undefined,
                  })
                  setCleanupResult(`deleted_jobs=${resp.deleted_jobs}`)
                  await loadJobs()
                } catch (err) {
                  setError((err as Error).message)
                }
              }}
            >
              执行 Job 清理
            </button>
          </div>
          {cleanupResult && (
            <p className="muted-text" style={{ marginTop: '0.25rem' }}>
              {cleanupResult}
            </p>
          )}
        </div>
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
