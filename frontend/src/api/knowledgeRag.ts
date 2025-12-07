import { http } from './http'

export type KnowledgeRagUsedChunk = {
  id: number
  document_id: number
  collection_id: number
  collection_name: string
  domain: string
  section_label?: string | null
  text: string
  score: number
  similarity: number
  importance: number
  metadata?: unknown
}

export type KnowledgeRagResponse = {
  used_chunks: KnowledgeRagUsedChunk[]
  debug: {
    total_candidates: number
    top_k: number
    avg_similarity_top_k: number
    avg_score_top_k: number
  }
}

export async function knowledgeRagQuery(payload: {
  project_id?: string
  collection_ids?: number[]
  domain?: string
  query: string
  top_k?: number
}): Promise<KnowledgeRagResponse> {
  return http.post<KnowledgeRagResponse>('/api/knowledge/rag/query', payload)
}
