/**
 * 多租户管理页面
 */
import { useState, useEffect } from 'react'
import { http } from '../api/http'
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
  email?: string
  display_name?: string
  group_id?: number
  tenant_id: number
  role?: string
  status?: string
}

interface ApiKey {
  id: number
  name: string
  key_prefix: string
  scopes: string[]
  status: string
  created_at: string
}

const API_BASE = 'http://localhost:5000/api'

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [groups, setGroups] = useState<UserGroup[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // 新建租户表单
  const [newTenantName, setNewTenantName] = useState('')
  const [newTenantCode, setNewTenantCode] = useState('')
  const [newTenantType, setNewTenantType] = useState('team')

  // 新建用户表单
  const [newUsername, setNewUsername] = useState('')
  const [newUserEmail, setNewUserEmail] = useState('')
  const [newUserDisplayName, setNewUserDisplayName] = useState('')
  const [newUserRole, setNewUserRole] = useState('member')

  // 新建 API Key 表单
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyScopes, setNewKeyScopes] = useState('*')
  const [createdKey, setCreatedKey] = useState<string | null>(null)

  // 加载租户列表
  const loadTenants = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await http.get<{ items: Tenant[] }>(`${API_BASE}/tenants`)
      setTenants(data.items || [])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 加载租户详情（用户组、用户、API Keys）
  const loadTenantDetails = async (tenant: Tenant, clearKey = true) => {
    setSelectedTenant(tenant)
    if (clearKey) setCreatedKey(null)
    try {
      const [groupsData, usersData, keysData] = await Promise.all([
        http.get<{ items: UserGroup[] }>(`${API_BASE}/tenants/${tenant.id}/groups`),
        http.get<{ items: User[] }>(`${API_BASE}/tenants/${tenant.id}/users`),
        http.get<{ items: ApiKey[] }>(`${API_BASE}/tenants/${tenant.id}/api-keys`),
      ])
      setGroups(groupsData.items || [])
      setUsers(usersData.items || [])
      setApiKeys(keysData.items || [])
    } catch (e) {
      console.error('加载租户详情失败:', e)
    }
  }

  // 创建用户
  const createUser = async () => {
    if (!selectedTenant || !newUsername.trim()) {
      setError('请选择租户并填写用户名')
      return
    }
    try {
      await http.post(`${API_BASE}/tenants/${selectedTenant.id}/users`, {
        username: newUsername,
        email: newUserEmail || undefined,
        display_name: newUserDisplayName || undefined,
        role: newUserRole,
      })
      setNewUsername('')
      setNewUserEmail('')
      setNewUserDisplayName('')
      setSuccess('用户创建成功')
      loadTenantDetails(selectedTenant)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // 删除用户
  const deleteUser = async (userId: number) => {
    if (!confirm('确定要删除此用户吗？')) return
    try {
      await http.delete(`${API_BASE}/users/${userId}`)
      setSuccess('用户已删除')
      if (selectedTenant) loadTenantDetails(selectedTenant)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // 创建 API Key
  const createApiKey = async () => {
    if (!selectedTenant || !newKeyName.trim()) {
      setError('请选择租户并填写密钥名称')
      return
    }
    try {
      const scopes = newKeyScopes === '*' ? ['*'] : newKeyScopes.split(',').map(s => s.trim())
      const data = await http.post<{ key: string }>(`${API_BASE}/tenants/${selectedTenant.id}/api-keys`, {
        name: newKeyName,
        scopes,
      })
      setCreatedKey(data.key)
      setNewKeyName('')
      setSuccess('API Key 创建成功，请复制保存！')
      loadTenantDetails(selectedTenant, false)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // 撤销 API Key
  const revokeApiKey = async (keyId: number) => {
    if (!confirm('确定要撤销此 API Key 吗？')) return
    try {
      await http.delete(`${API_BASE}/api-keys/${keyId}`)
      if (selectedTenant) loadTenantDetails(selectedTenant)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // 重新生成 API Key（密钥丢失时使用）
  const regenerateApiKey = async (keyId: number) => {
    if (!confirm('确定要重新生成此 API Key 吗？旧密钥将失效！')) return
    try {
      const data = await http.post<{ key: string }>(`${API_BASE}/api-keys/${keyId}/regenerate`, {})
      setCreatedKey(data.key)
      setSuccess('新密钥已生成，请立即复制保存！')
      if (selectedTenant) loadTenantDetails(selectedTenant, false)
    } catch (e) {
      setError((e as Error).message)
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
      await http.post(`${API_BASE}/tenants`, { name: newTenantName, code: newTenantCode, type: newTenantType })
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
        <h3 style={{ marginBottom: '1rem' }}>创建租户（project_id = 租户编码）</h3>
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
            <label className="label">租户编码 (project_id)</label>
            <input
              type="text"
              value={newTenantCode}
              onChange={(e) => setNewTenantCode(e.target.value)}
              placeholder="例如：MYPROJECT"
            />
          </div>
          <div style={{ flex: 0.5 }}>
            <label className="label">类型</label>
            <select value={newTenantType} onChange={(e) => setNewTenantType(e.target.value)}>
              <option value="personal">个人</option>
              <option value="team">团队</option>
              <option value="enterprise">企业</option>
            </select>
          </div>
          <button onClick={createTenant} disabled={loading}>
            {loading ? '创建中...' : '创建租户'}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger" style={{ marginBottom: '1rem' }}>{error}</div>}
      {success && <div className="alert alert-success" style={{ marginBottom: '1rem' }}>{success}</div>}

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
              {/* 用户组 */}
              <div style={{ marginBottom: '1rem' }}>
                <h4>用户组 ({groups.length})</h4>
                {groups.length === 0 ? (
                  <div className="empty-state" style={{ padding: '0.5rem' }}>暂无用户组</div>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                    {groups.map((g) => (
                      <li key={g.id}>{g.name} (ID: {g.id})</li>
                    ))}
                  </ul>
                )}
              </div>

              {/* 用户管理 */}
              <div style={{ marginBottom: '1rem' }}>
                <h4>用户 ({users.length})</h4>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="用户名 *"
                    style={{ flex: '1 1 100px' }}
                  />
                  <input
                    type="email"
                    value={newUserEmail}
                    onChange={(e) => setNewUserEmail(e.target.value)}
                    placeholder="邮箱"
                    style={{ flex: '1 1 150px' }}
                  />
                  <input
                    type="text"
                    value={newUserDisplayName}
                    onChange={(e) => setNewUserDisplayName(e.target.value)}
                    placeholder="显示名称"
                    style={{ flex: '1 1 100px' }}
                  />
                  <select value={newUserRole} onChange={(e) => setNewUserRole(e.target.value)} style={{ width: '80px' }}>
                    <option value="member">成员</option>
                    <option value="admin">管理员</option>
                    <option value="viewer">只读</option>
                  </select>
                  <button onClick={createUser}>添加</button>
                </div>
                {users.length === 0 ? (
                  <div className="empty-state" style={{ padding: '0.5rem' }}>暂无用户</div>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                    {users.map((u) => (
                      <li key={u.id} style={{ marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <strong>{u.username}</strong>
                        {u.display_name && <span>({u.display_name})</span>}
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          [{u.role || 'member'}]
                        </span>
                        {u.email && <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{u.email}</span>}
                        <button 
                          onClick={() => deleteUser(u.id)}
                          style={{ 
                            marginLeft: 'auto',
                            background: '#dc2626', 
                            color: 'white', 
                            border: 'none',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                          }}
                        >
                          删除
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* API Key 管理 */}
              <div>
                <h4>API Keys ({apiKeys.length})</h4>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <input
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder="密钥名称"
                    style={{ flex: 1 }}
                  />
                  <input
                    type="text"
                    value={newKeyScopes}
                    onChange={(e) => setNewKeyScopes(e.target.value)}
                    placeholder="权限范围"
                    style={{ width: '120px' }}
                    title="* 表示全部权限，或用逗号分隔"
                  />
                  <button onClick={createApiKey}>创建</button>
                </div>
                {createdKey && (
                  <div style={{ 
                    background: '#1a472a', 
                    border: '2px solid #4ade80', 
                    borderRadius: '8px',
                    padding: '1rem', 
                    marginBottom: '1rem',
                  }}>
                    <div style={{ color: '#4ade80', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                      ⚠️ 密钥只显示一次，请立即复制保存！
                    </div>
                    <div style={{ 
                      background: '#0d1117', 
                      padding: '0.75rem', 
                      borderRadius: '4px',
                      fontFamily: 'monospace',
                      fontSize: '0.9rem',
                      wordBreak: 'break-all',
                      marginBottom: '0.5rem',
                      color: '#e6edf3',
                    }}>
                      {createdKey}
                    </div>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(createdKey)
                        setSuccess('密钥已复制到剪贴板！')
                      }}
                      style={{ 
                        background: '#238636', 
                        color: 'white', 
                        border: 'none',
                        padding: '0.5rem 1rem',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                      }}
                    >
                      📋 复制密钥
                    </button>
                  </div>
                )}
                {apiKeys.length === 0 ? (
                  <div className="empty-state" style={{ padding: '0.5rem' }}>暂无 API Key</div>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                    {apiKeys.map((k) => (
                      <li key={k.id} style={{ marginBottom: '0.25rem' }}>
                        <strong>{k.name}</strong> ({k.key_prefix}...)
                        <span style={{ marginLeft: '0.5rem', color: k.status === 'active' ? 'green' : 'red' }}>
                          [{k.status}]
                        </span>
                        {k.status === 'active' && (
                          <>
                            <button 
                              onClick={() => regenerateApiKey(k.id)} 
                              style={{ marginLeft: '0.5rem', padding: '0.1rem 0.3rem', fontSize: '0.75rem' }}
                              title="密钥丢失时重新生成"
                            >
                              🔄 重新生成
                            </button>
                            <button 
                              onClick={() => revokeApiKey(k.id)} 
                              style={{ marginLeft: '0.25rem', padding: '0.1rem 0.3rem', fontSize: '0.75rem', color: 'red' }}
                            >
                              撤销
                            </button>
                          </>
                        )}
                      </li>
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
