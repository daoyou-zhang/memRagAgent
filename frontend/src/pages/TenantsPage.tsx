/**
 * 多租户管理页面
 */
import { useState, useEffect } from 'react'
import '../App.css'

interface Tenant {
  id: number
  name: string
  code: string
  status: string
  created_at: string
}

interface UserGroup {
  id: number
  name: string
  tenant_id: number
}

interface User {
  id: number
  username: string
  group_id: number
  tenant_id: number
}

const API_BASE = 'http://localhost:5000'

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [groups, setGroups] = useState<UserGroup[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 新建租户表单
  const [newTenantName, setNewTenantName] = useState('')
  const [newTenantCode, setNewTenantCode] = useState('')

  // 加载租户列表
  const loadTenants = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/tenants`)
      const data = await res.json()
      setTenants(data.tenants || [])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 加载租户详情（用户组和用户）
  const loadTenantDetails = async (tenant: Tenant) => {
    setSelectedTenant(tenant)
    try {
      const [groupsRes, usersRes] = await Promise.all([
        fetch(`${API_BASE}/api/tenants/${tenant.id}/groups`),
        fetch(`${API_BASE}/api/tenants/${tenant.id}/users`),
      ])
      const groupsData = await groupsRes.json()
      const usersData = await usersRes.json()
      setGroups(groupsData.groups || [])
      setUsers(usersData.users || [])
    } catch (e) {
      console.error('加载租户详情失败:', e)
    }
  }

  // 创建租户
  const createTenant = async () => {
    if (!newTenantName.trim() || !newTenantCode.trim()) {
      setError('请填写租户名称和编码')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/tenants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newTenantName, code: newTenantCode }),
      })
      if (!res.ok) throw new Error('创建失败')
      setNewTenantName('')
      setNewTenantCode('')
      loadTenants()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTenants()
  }, [])

  return (
    <div className="page-container">
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ marginBottom: '1rem' }}>创建租户</h3>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label className="label">租户名称</label>
            <input
              type="text"
              value={newTenantName}
              onChange={(e) => setNewTenantName(e.target.value)}
              placeholder="例如：测试公司"
            />
          </div>
          <div style={{ flex: 1 }}>
            <label className="label">租户编码</label>
            <input
              type="text"
              value={newTenantCode}
              onChange={(e) => setNewTenantCode(e.target.value)}
              placeholder="例如：test_company"
            />
          </div>
          <button onClick={createTenant} disabled={loading}>
            {loading ? '创建中...' : '创建租户'}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* 租户列表 */}
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>租户列表</h3>
          {loading ? (
            <div className="loading">加载中...</div>
          ) : tenants.length === 0 ? (
            <div className="empty-state">暂无租户</div>
          ) : (
            <div className="list">
              {tenants.map((tenant) => (
                <div
                  key={tenant.id}
                  className={`list-item ${selectedTenant?.id === tenant.id ? 'active' : ''}`}
                  onClick={() => loadTenantDetails(tenant)}
                  style={{ cursor: 'pointer', padding: '0.75rem', borderRadius: '0.5rem' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <strong>{tenant.name}</strong>
                    <span className="badge">{tenant.code}</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    状态: {tenant.status} | ID: {tenant.id}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 租户详情 */}
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>
            {selectedTenant ? `${selectedTenant.name} 详情` : '选择租户查看详情'}
          </h3>
          {selectedTenant ? (
            <>
              <div style={{ marginBottom: '1rem' }}>
                <h4>用户组 ({groups.length})</h4>
                {groups.length === 0 ? (
                  <div className="empty-state" style={{ padding: '1rem' }}>暂无用户组</div>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                    {groups.map((g) => (
                      <li key={g.id}>{g.name} (ID: {g.id})</li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h4>用户 ({users.length})</h4>
                {users.length === 0 ? (
                  <div className="empty-state" style={{ padding: '1rem' }}>暂无用户</div>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                    {users.map((u) => (
                      <li key={u.id}>{u.username} (ID: {u.id})</li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state">请从左侧选择一个租户</div>
          )}
        </div>
      </div>
    </div>
  )
}
