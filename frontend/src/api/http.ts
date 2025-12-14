const JSON_HEADERS: HeadersInit = { 'Content-Type': 'application/json' }

// ============================================================
// API Key 管理
// ============================================================
const API_KEY_STORAGE_KEY = 'memrag_api_key'
const PROJECT_ID_STORAGE_KEY = 'memrag_project_id'

export function getApiKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE_KEY)
}

export function setApiKey(key: string): void {
  localStorage.setItem(API_KEY_STORAGE_KEY, key)
}

export function clearApiKey(): void {
  localStorage.removeItem(API_KEY_STORAGE_KEY)
}

export function getProjectId(): string | null {
  return localStorage.getItem(PROJECT_ID_STORAGE_KEY)
}

export function setProjectId(id: string): void {
  localStorage.setItem(PROJECT_ID_STORAGE_KEY, id)
}

// ============================================================
// HTTP 请求（自动带认证头）
// ============================================================
function getAuthHeaders(): HeadersInit {
  const headers: Record<string, string> = {}
  
  const apiKey = getApiKey()
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }
  
  const projectId = getProjectId()
  if (projectId) {
    headers['X-Project-Id'] = projectId
  }
  
  return headers
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    headers: {
      ...JSON_HEADERS,
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    
    // 认证失败提示
    if (res.status === 401) {
      console.error('[Auth] API Key 无效或未设置，请在设置中配置')
    }
    
    throw new Error(`HTTP ${res.status}: ${text}`)
  }

  // 调用方约定响应为 JSON
  return (await res.json()) as T
}

export const http = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body: unknown) =>
    request<T>(url, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(url: string, body: unknown) =>
    request<T>(url, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
}
