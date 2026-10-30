import { reactive, readonly } from 'vue'
import { getSpotifyStatus } from '../api'

// One app-wide copy, shared by every importer: the banner reads it, `api.js`
// writes to it when any request comes back `spotify_auth_revoked`.
const state = reactive({
  authOk: true,
  errorAt: null, // ISO string, first failure (from the backend)
  message: null,
  checking: false,
  notice: null, // { kind: 'success' | 'error', text } after returning from /login
})

let inflight = null
let watching = false
let noticeTimer = null

const RETURN_ERRORS = {
  access_denied: 'Spotify login was cancelled.',
  invalid_state: 'The login link expired — please try again.',
  token_exchange_failed: "Spotify didn't accept the login — please try again.",
  wrong_account:
    'That Spotify account isn’t the one this library belongs to. Log in with the original ' +
    'account — or, to switch accounts on purpose, use the terminal login below.',
}

export function markSpotifyAuthRevoked(message) {
  state.authOk = false
  state.message = message
  state.errorAt ??= new Date().toISOString() // the next check() brings the real one
}

// Concurrent calls share one request (focus + visibilitychange fire together).
function check() {
  if (inflight) return inflight
  state.checking = true
  inflight = getSpotifyStatus()
    .then((s) => {
      state.authOk = s.auth_ok
      state.errorAt = s.error_at
      state.message = s.message
    })
    .catch(() => {}) // backend unreachable: keep the last known state
    .finally(() => {
      state.checking = false
      inflight = null
    })
  return inflight
}

function setNotice(kind, text) {
  clearTimeout(noticeTimer)
  state.notice = { kind, text }
  if (kind === 'success') noticeTimer = setTimeout(() => (state.notice = null), 5000)
}

// Outcome of the /login → /callback round trip, passed back as `?spotify=`.
function handleReturn(result, reason) {
  if (result === 'reconnected') setNotice('success', 'Reconnected to Spotify.')
  else setNotice('error', RETURN_ERRORS[reason] ?? `Reconnecting failed (${reason ?? 'unknown error'}).`)
  return check()
}

function dismissNotice() {
  clearTimeout(noticeTimer)
  state.notice = null
}

// Check on load and whenever the app regains attention — a scheduled refresh
// may have hit the error while the tab sat in the background. No polling.
// Listeners live as long as the app (called once, from App.vue).
function startWatching() {
  if (watching) return
  watching = true
  check()
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') check()
  })
  window.addEventListener('focus', check)
}

export function useSpotifyStatus() {
  return { status: readonly(state), check, startWatching, handleReturn, dismissNotice }
}
