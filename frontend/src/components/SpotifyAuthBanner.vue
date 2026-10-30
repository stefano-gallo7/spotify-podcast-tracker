<script setup>
import { computed, ref } from 'vue'
import { spotifyLoginUrl } from '../api'
import { useSpotifyStatus } from '../composables/useSpotifyStatus'

const { status, check, dismissNotice } = useSpotifyStatus()

const TERMINAL_CMD = 'python -m scripts.spotify_login'
const copied = ref(false)

const since = computed(() =>
  status.errorAt
    ? new Date(status.errorAt).toLocaleString(undefined, {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null,
)

// Same tab: the OAuth round trip lands back on the app anyway.
function reconnect() {
  window.location.href = spotifyLoginUrl()
}

async function copyCommand() {
  try {
    await navigator.clipboard.writeText(TERMINAL_CMD)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    // Clipboard blocked: the command is on screen to copy by hand.
  }
}
</script>

<template>
  <!-- No dismiss: refreshes are stopped until this is fixed, so it stays up. -->
  <section v-if="!status.authOk" class="banner warning" role="alert">
    <div class="row">
      <p class="text">
        <strong>Spotify connection lost</strong><span v-if="since"> since {{ since }}</span>.
        Automatic refreshes are paused; your library is still available.
      </p>
      <div class="actions">
        <button type="button" class="primary" @click="reconnect">Reconnect</button>
        <button type="button" class="link" :disabled="status.checking" @click="check">
          {{ status.checking ? 'Checking…' : 'Recheck' }}
        </button>
      </div>
    </div>

    <p v-if="status.notice?.kind === 'error'" class="notice-error">{{ status.notice.text }}</p>

    <details>
      <summary>Fix from the terminal instead</summary>
      <p>From the project root (the backend can keep running), then click Recheck:</p>
      <div class="cmd">
        <code>{{ TERMINAL_CMD }}</code>
        <button type="button" class="link" @click="copyCommand">{{ copied ? 'Copied' : 'Copy' }}</button>
      </div>
      <p v-if="status.message" class="detail">Details: {{ status.message }}</p>
    </details>
  </section>

  <section v-else-if="status.notice?.kind === 'success'" class="banner success" role="status">
    <div class="row">
      <p class="text">{{ status.notice.text }}</p>
      <button type="button" class="link" aria-label="Dismiss" @click="dismissNotice">✕</button>
    </div>
  </section>
</template>

<style scoped>
.banner {
  margin: 0 auto 24px;
  max-width: 960px;
  padding: 12px 16px;
  border: 1px solid;
  border-radius: 8px;
  font-size: 15px;
  line-height: 140%;
}

.warning {
  background: var(--warning-bg);
  border-color: var(--warning-border);
  color: var(--warning-text);
}

.success {
  background: var(--success-bg);
  border-color: var(--success-border);
  color: var(--success-text);
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.text {
  flex: 1 1 320px;
}

.text strong {
  font-weight: 600;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

button {
  font-family: var(--sans);
  font-size: 14px;
  cursor: pointer;
}

button:disabled {
  cursor: default;
  opacity: 0.6;
}

.primary {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  background: var(--warning-text);
  color: var(--bg);
  font-weight: 500;
}

.link {
  padding: 0;
  border: none;
  background: none;
  color: inherit;
  text-decoration: underline;
}

.notice-error {
  margin-top: 8px;
  font-weight: 500;
}

details {
  margin-top: 8px;
}

summary {
  cursor: pointer;
  width: fit-content;
}

details p {
  margin-top: 6px;
}

.cmd {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 6px;
}

.cmd code {
  max-width: 100%;
  overflow-x: auto;
}

.detail {
  font-size: 13px;
  opacity: 0.85;
  overflow-wrap: anywhere;
}
</style>
