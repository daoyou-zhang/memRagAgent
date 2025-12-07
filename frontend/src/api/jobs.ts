import { http } from './http'

export type MemoryJob = {
  id: number
  user_id: string | null
  agent_id: string | null
  project_id: string | null
  session_id: string
  start_message_id: number | null
  end_message_id: number | null
  job_type: string
  target_types: unknown
  status: string
  error_message?: string | null
  created_at: string
  updated_at: string
}

export type ListJobsResponse = {
  items: MemoryJob[]
}

export type CleanupJobsRequest = {
  status?: string[]
  before?: string
  user_id?: string
  project_id?: string
}

export type CleanupJobsResponse = {
  deleted_jobs: number
  status?: string[]
  user_id?: string
  project_id?: string
  before?: string
}

export type CreateEpisodicJobPayload = {
  user_id?: string
  agent_id?: string
  project_id?: string
  session_id: string
  start_message_id?: number
  end_message_id?: number
}

export async function createEpisodicJob(
  payload: CreateEpisodicJobPayload,
): Promise<MemoryJob> {
  return http.post<MemoryJob>('/api/memory/jobs/episodic', payload)
}

export async function createSemanticJob(
  payload: CreateEpisodicJobPayload,
): Promise<MemoryJob> {
  return http.post<MemoryJob>('/api/memory/jobs/semantic', payload)
}

export async function createProfileJob(payload: Pick<CreateEpisodicJobPayload, 'user_id' | 'project_id'>): Promise<MemoryJob> {
  return http.post<MemoryJob>('/api/memory/jobs/profile', payload)
}

export async function closeSession(sessionId: string): Promise<{
  status: string
  session_id: string
  auto_episodic_enabled: boolean
  auto_semantic_enabled: boolean
  auto_profile_enabled: boolean
  message_count: number
  episodic_min_messages: number
  semantic_min_messages: number
  created_jobs: Array<{
    id: number
    job_type: string
    session_id: string
    user_id: string | null
    project_id: string | null
    status: string
  }>
}> {
  return http.post(`/api/memory/sessions/${encodeURIComponent(sessionId)}/close`, {})
}

export async function createProfileJobAuto(payload: {
  user_id: string
  project_id?: string
  min_new_semantic?: number
  session_id?: string
}): Promise<{
  status: 'created' | 'no_need'
  user_id: string
  project_id?: string | null
  new_semantic_count: number
  min_new_semantic: number
  job?: MemoryJob
}> {
  return http.post('/api/memory/jobs/profile/auto', payload)
}

export async function listJobs(params?: {
  status?: string
  session_id?: string
}): Promise<ListJobsResponse> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.session_id) qs.set('session_id', params.session_id)
  const suffix = qs.toString() ? `?${qs.toString()}` : ''
  return http.get<ListJobsResponse>(`/api/memory/jobs${suffix}`)
}

export async function cleanupJobs(payload: CleanupJobsRequest): Promise<CleanupJobsResponse> {
  return http.post<CleanupJobsResponse>('/api/memory/jobs/cleanup', payload)
}

export async function runJob(jobId: number): Promise<{
  job: { id: number; status: string; updated_at: string }
  memory?: {
    id: number
    type: string
    source: string
    text: string
    importance: number
    tags?: unknown
    metadata?: unknown
  }
}> {
  return http.post(`/api/memory/jobs/${jobId}/run`, {})
}
