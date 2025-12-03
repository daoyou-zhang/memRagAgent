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
