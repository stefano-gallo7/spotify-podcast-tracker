const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, options)
  if (!response.ok) {
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
