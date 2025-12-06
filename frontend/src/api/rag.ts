import { http } from './http'

export type RagQueryPayload = {
  project_id: string
  user_id?: string
  agent_id?: string
  /** 预留给将来的模式切换，目前后端忽略 */
  mode?: string
  query: string
  top_k?: number
}

export type RagContextItem = {
  type: 'doc' | 'memory' | 'graph'
  id: string
  text: string
  /** 综合得分：基于相似度 + importance + recency + type_boost */
  score: number
  /** 纯向量相似度（余弦） */
  similarity?: number
  importance?: number
  recency?: number
  memory_type?: string
}

export type RagQueryResponse = {
  answer: string
  used_context?: RagContextItem[]
  debug_info?: Record<string, unknown>
}

export async function ragQuery(
  payload: RagQueryPayload,
): Promise<RagQueryResponse> {
  return http.post<RagQueryResponse>('/api/rag/query', payload)
}
