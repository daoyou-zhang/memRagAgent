/**
 * 道友认知 API (daoyou_agent)
 *
 * 后端端口：8000（与 memory 服务的 5000 不同）
 */

export const DAOYOU_BASE = 'http://127.0.0.1:8000'

export interface CognitiveRequest {
  input: string
  user_id?: string
  session_id?: string
  project_id?: string
  context?: Record<string, unknown>
  enable_memory?: boolean
  memory_depth?: number
  rag_level?: number
  enable_tools?: boolean
  enable_learning?: boolean
  quality_level?: 'fast' | 'balanced' | 'high'
  // 自定义 Prompt（可选）
  intent_system_prompt?: string
  intent_user_prompt?: string
  response_system_prompt?: string
  response_user_prompt?: string
}

export interface Intent {
  category: string
  confidence: number
  entities: Array<{ type: string; value: string }>
  query: string
  context: Record<string, unknown>
  summary?: string
  needs_tool?: boolean
  suggested_tools?: string[]
}

export interface CognitiveResponse {
  content: string
  intent?: Intent
  confidence?: number
  reasoning_steps?: Array<Record<string, unknown>>
  sources?: Array<Record<string, unknown>>
  tool_results?: Record<string, unknown>
  performance_metrics?: Record<string, unknown>
  processing_time?: number
  tokens_used?: number
  ai_service_used?: string
  timestamp?: string
  session_id?: string
  user_id?: string
}

export async function cognitiveProcess(
  req: CognitiveRequest
): Promise<CognitiveResponse> {
  const res = await fetch(`${DAOYOU_BASE}/api/v1/cognitive/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text}`)
  }

  return (await res.json()) as CognitiveResponse
}
