import { markSpotifyAuthRevoked } from './composables/useSpotifyStatus'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

// The backend's Spotify login is dead (revoked / missing); only reconnecting fixes it.
export class SpotifyAuthError extends Error {}

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, options)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if (body?.code === 'spotify_auth_revoked') {
      // Raise the banner now, without waiting for the next status check.
      markSpotifyAuthRevoked(body.detail)
      throw new SpotifyAuthError(body.detail)
    }
    throw new Error(`API returned ${response.status}`)
  }
  return response.json()
}

export function listShows(params) {
  const query = params instanceof URLSearchParams ? params : new URLSearchParams(params)
  return request(`/api/shows?${query}`)
}

export function getShow(id) {
  return request(`/api/shows/${id}`)
}

export function listEpisodes({ inProgress, showStatus, limit = 20 } = {}) {
  const query = new URLSearchParams({ limit })
  if (inProgress !== undefined) query.set('in_progress', inProgress)
  if (showStatus) query.set('show_status', showStatus)
  return request(`/api/episodes?${query}`)
}

export function getEpisode(id) {
  return request(`/api/episodes/${id}`)
}

export function updateShow(id, patch) {
  return request(`/api/shows/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
}

export function updateEpisode(id, patch) {
  return request(`/api/episodes/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
}

export function searchSpotifyShows(q) {
  return request(`/api/spotify/search?q=${encodeURIComponent(q)}`)
}

export function getSpotifyStatus() {
  return request('/api/spotify/status')
}

// A page the browser navigates to (it redirects on to Spotify), not a fetch.
export function spotifyLoginUrl() {
  return `${BASE}/api/spotify/login`
}

export function addShowByUri(uri) {
  return request('/api/shows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uri }),
  })
}

export function listTags() {
  return request('/api/tags')
}

export function addShowTag(showId, name) {
  return request(`/api/shows/${showId}/tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

export function removeShowTag(showId, name) {
  return request(`/api/shows/${showId}/tags/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  })
}

// --- Stats / dashboard ------------------------------------------------------

export function getStatsOverview() {
  return request('/api/stats/overview')
}

export function getTopShows({ limit = 10, by = 'hours' } = {}) {
  const query = new URLSearchParams({ limit, by })
  return request(`/api/stats/top-shows?${query}`)
}

export function getActivity({ months = 12, resolution = 'month', endOffset = 0 } = {}) {
  const query = new URLSearchParams({ months, resolution, end_offset: endOffset })
  return request(`/api/stats/activity?${query}`)
}

export function getStatsByTag({ by = 'hours' } = {}) {
  const query = new URLSearchParams({ by })
  return request(`/api/stats/by-tag?${query}`)
}
