import { useState, useEffect } from 'react'
import { getApiKey, setApiKey, clearApiKey, getProjectId, setProjectId } from '../api/http'

export default function SettingsPage() {
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [projectIdInput, setProjectIdInput] = useState('')
  const [saved, setSaved] = useState(false)
  const [hasApiKey, setHasApiKey] = useState(false)

  useEffect(() => {
    // 加载已保存的配置
    const savedKey = getApiKey()
    const savedProject = getProjectId()
    
    if (savedKey) {
      setApiKeyInput(savedKey)
      setHasApiKey(true)
    }
    if (savedProject) {
      setProjectIdInput(savedProject)
    }
  }, [])

  const handleSave = () => {
    if (apiKeyInput.trim()) {
      setApiKey(apiKeyInput.trim())
      setHasApiKey(true)
    }
    if (projectIdInput.trim()) {
      setProjectId(projectIdInput.trim())
    }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleClear = () => {
    clearApiKey()
    setApiKeyInput('')
    setHasApiKey(false)
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <span className="text-3xl">⚙️</span>
        <h1 className="text-2xl font-bold text-white">设置</h1>
      </div>

      {/* API Key 配置 */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xl">🔑</span>
          <h2 className="text-lg font-semibold text-white">API 认证</h2>
          {hasApiKey && (
            <span className="ml-2 px-2 py-0.5 bg-green-900/50 text-green-400 text-xs rounded">
              已配置
            </span>
          )}
        </div>
        
        <p className="text-gray-400 text-sm mb-4">
          配置 API Key 后，所有请求将自动携带认证信息。
          管理员可使用 ADMIN_API_KEY 获得完全访问权限。
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">API Key</label>
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="sk-xxxxxxxx"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* 项目配置 */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xl">📁</span>
          <h2 className="text-lg font-semibold text-white">项目配置</h2>
        </div>
        
        <p className="text-gray-400 text-sm mb-4">
          设置默认项目 ID，用于区分不同项目的数据。
          其他工程调用 API 时，会通过此 ID 隔离数据。
        </p>

        <div>
          <label className="block text-sm text-gray-300 mb-1">项目 ID</label>
          <input
            type="text"
            value={projectIdInput}
            onChange={(e) => setProjectIdInput(e.target.value)}
            placeholder="my-project-001"
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-4">
        <button
          onClick={handleSave}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
        >
          {saved ? '✅' : '💾'} {saved ? '已保存' : '保存设置'}
        </button>
        
        <button
          onClick={handleClear}
          className="flex items-center gap-2 bg-red-600/20 hover:bg-red-600/40 text-red-400 px-4 py-2 rounded transition-colors"
        >
          🗑️ 清除 API Key
        </button>
      </div>

      {/* 使用说明 */}
      <div className="mt-8 bg-gray-800/50 rounded-lg p-4 border border-gray-700">
        <h3 className="text-sm font-semibold text-gray-300 mb-2">📖 其他工程调用 API</h3>
        <div className="text-sm text-gray-400 space-y-2">
          <p>其他工程调用 API 时，需要在请求头中携带：</p>
          <pre className="bg-gray-900 p-2 rounded text-xs overflow-x-auto">
{`// HTTP 请求头
X-API-Key: sk-your-api-key
X-Project-Id: your-project-id

// 或使用 Bearer Token
Authorization: Bearer sk-your-api-key`}
          </pre>
          <p className="text-yellow-400/80">
            ⚠️ 不同项目使用不同的 project_id，数据自动隔离
          </p>
        </div>
      </div>
    </div>
  )
}
