import { http } from './http'

export type HealthResponse = {
  status: string
  service: string
  version: string
}

export type Memory = {
  id: number
  user_id: string | null
  agent_id: string | null
  project_id: string | null
  type: string
  source: string
  text: string
  importance: number
  tags?: string[]
  created_at?: string | null
}

export type QueryResultItem = {
  memory: Memory
  score: number
}

export async function fetchMemoryHealth(): Promise<HealthResponse> {
  return http.get<HealthResponse>('/api/memory/health')
}

export type CreateMemoryPayload = {
  user_id?: string
  agent_id?: string
  project_id?: string
  type: string
  source?: string
  text: string
  importance?: number
  tags?: string[]
  metadata?: unknown
}

export async function createMemory(payload: CreateMemoryPayload): Promise<Memory> {
  return http.post<Memory>('/api/memory/memories', payload)
}

export type QueryMemoriesPayload = {
  user_id?: string
  project_id?: string
  query?: string
  top_k?: number
  page?: number
  page_size?: number
  filters?: {
    types?: string[]
    min_importance?: number
    tags?: string[]
  }
}

export type QueryMemoriesResponse = {
  items: QueryResultItem[]
  page: number
  page_size: number
  total: number
  has_next: boolean
  has_prev: boolean
}

export async function queryMemories(
  payload: QueryMemoriesPayload,
): Promise<QueryMemoriesResponse> {
  return http.post<QueryMemoriesResponse>(
    '/api/memory/memories/query',
    payload,
  )
}

export type FullContextPayload = {
  user_id?: string
  project_id: string
  session_id: string
  query?: string
  recent_message_limit?: number
  rag_top_k?: number
}

export type FullContextWorkingMessage = {
  id: number
  role: string
  content: string
  created_at?: string | null
}

export type FullContextRagMemory = {
  type: string
  id: string
  text: string
  score: number
  similarity?: number
  importance?: number
  recency?: number
  memory_type?: string
}

export type FullContextResponse = {
  profile: unknown | null
  working_messages: FullContextWorkingMessage[]
  rag_memories: FullContextRagMemory[]
  rag_debug: {
    total_candidates: number
    top_k: number
    avg_similarity_top_k: number
    avg_score_top_k: number
  }
}

export async function fetchFullContext(
  payload: FullContextPayload,
): Promise<FullContextResponse> {
  return http.post<FullContextResponse>('/api/memory/context/full', payload)
}
