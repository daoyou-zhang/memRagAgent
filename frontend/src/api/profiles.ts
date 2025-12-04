import { http } from './http'

export type SemanticMemoryItem = {
  id: number
  text: string
  tags?: unknown
  importance: number
  created_at: string | null
}

export type RawProfilePayload = {
  user_id: string
  project_id?: string | null
  profile: {
    user_id: string
    project_id?: string | null
    raw_semantic_memories: SemanticMemoryItem[]
  }
}

export async function getUserProfile(
  userId: string,
  projectId?: string,
  forceRefresh?: boolean,
): Promise<RawProfilePayload> {
  const params = new URLSearchParams()
  if (projectId) params.set('project_id', projectId)
  if (forceRefresh) params.set('force_refresh', 'true')
  const qs = params.toString()
  const suffix = qs ? `?${qs}` : ''
  return http.get<RawProfilePayload>(`/api/profiles/${encodeURIComponent(userId)}${suffix}`)
}
