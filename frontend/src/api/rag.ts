import { http } from './http'

export type RagQueryPayload = {
  project_id: string
  user_id?: string
  agent_id?: string
  mode?: string
  query: string
}

export type RagContextItem = {
  type: 'doc' | 'memory' | 'graph'
  id: string
  text: string
  score: number
}

export type RagQueryResponse = {
  answer: string
  used_context?: RagContextItem[]
  debug_info?: Record<string, unknown>
}

export async function ragQuery(
  payload: RagQueryPayload,
): Promise<RagQueryResponse> {
  // 后端还没实现时，这里只是占位，方便后续接通
  return http.post<RagQueryResponse>('/api/rag/query', payload)
}
