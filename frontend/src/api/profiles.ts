import { http } from './http'

export type UserProfile = {
  user_id: string
  preferences?: Record<string, unknown>
  skills?: string[]
  interests?: string[]
  summary?: string
}

export async function getUserProfile(
  userId: string,
): Promise<UserProfile> {
  // 对应未来的 GET /api/memory/profiles/user/:user_id
  return http.get<UserProfile>(`/api/memory/profiles/user/${userId}`)
}
