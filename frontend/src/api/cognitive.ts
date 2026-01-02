// DaoyouAgent Cognitive API typings and helper
// 前端与 /api/v1/cognitive/process 交互的统一封装

export const DAOYOU_BASE: string =
  (import.meta as any).env?.VITE_DAOYOU_BASE || 'http://localhost:8000'

// -------- 数据模型（需与后端 Pydantic 模型保持一致） --------

export interface Intent {
  category: string
  confidence: number
  entities?: Array<Record<string, any>>
  query?: string
  context?: Record<string, any> | null
  summary?: string | null
  needs_tool?: boolean
  suggested_tools?: string[]
}

export interface ReasoningStep {
  step: string
  detail: string
  timestamp: string
}

export interface PerformanceMetrics {
  processing_time: number
  tokens_used: number
}

export interface CognitiveRequest {
  // 基本会话信息
  input: string
  user_id?: string
  session_id?: string
  project_id?: string

  // Agent / 人格标识
  agent_id?: string

  // 控制选项
  stream?: boolean
  enable_intent?: boolean
  enable_memory?: boolean
  memory_depth?: number
  rag_level?: number
  enable_tools?: boolean
  enable_learning?: boolean

  // 额外上下文
  context?: Record<string, any>

  // Prompt 覆盖
  intent_system_prompt?: string
  intent_user_prompt?: string
  response_system_prompt?: string
  response_user_prompt?: string

  // 行业/领域（兼容字段）
  industry?: string

  // 自定义模型配置
  model_config_override?: Record<string, any>
}

export interface CognitiveResponse {
  content: string
  intent?: Intent
  confidence: number

  processing_time: number
  ai_service_used?: string
  tokens_used: number

  session_id?: string
  user_id?: string
  tool_used?: string

  reasoning_steps?: ReasoningStep[]
  metrics?: PerformanceMetrics
}

// -------- 请求封装（非流式，stream=false） --------

export async function cognitiveProcess(
  payload: CognitiveRequest,
  options?: { signal?: AbortSignal },
): Promise<CognitiveResponse> {
  const resp = await fetch(`/api/v1/cognitive/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, stream: false }),
    signal: options?.signal,
  })

  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(`Cognitive API error ${resp.status}: ${text || resp.statusText}`)
  }

  return (await resp.json()) as CognitiveResponse
}
