import { useState, type FormEvent } from 'react'
import { getUserProfile, type UserProfile } from '../api/profiles'

function ProfilesPage() {
  const [userId, setUserId] = useState('u_123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setProfile(null)
    try {
      const data = await getUserProfile(userId)
      setProfile(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '1rem', maxWidth: 900, margin: '0 auto' }}>
      <h2>User Profile</h2>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.5rem' }}>
        <div>
          <label>
            User ID:{' '}
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </label>
        </div>
        <button type="submit" disabled={loading || !userId.trim()}>
          {loading ? 'Loading...' : 'Load Profile'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {profile && (
        <div style={{ marginTop: '1rem' }}>
          <h3>User: {profile.user_id}</h3>
          {profile.summary && <p>{profile.summary}</p>}
          {profile.skills && (
            <p>
              <strong>Skills:</strong> {profile.skills.join(', ')}
            </p>
          )}
          {profile.interests && (
            <p>
              <strong>Interests:</strong> {profile.interests.join(', ')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default ProfilesPage
