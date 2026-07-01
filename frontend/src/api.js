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
