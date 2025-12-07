import { http } from './http'

export type CleanupMode = 'by_user' | 'by_time' | 'by_limit'

export interface CleanupRequest {
  mode: CleanupMode
  user_id?: string
  project_id?: string
  types?: ('episodic' | 'semantic')[]
  before?: string
  max_keep?: number
  delete_profile?: boolean
}

export interface CleanupResponse {
  mode: CleanupMode
  user_id?: string
  project_id?: string
  types: string[]
  deleted_memories: number
  deleted_embeddings: number
  deleted_profiles: number
}

export async function cleanupMemories(payload: CleanupRequest): Promise<CleanupResponse> {
  return http.post<CleanupResponse>('/api/memory/memories/cleanup', payload)
}
