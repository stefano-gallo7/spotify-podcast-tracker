<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { lastLibraryQuery } from './router'
import SpotifyAuthBanner from './components/SpotifyAuthBanner.vue'
import { useSpotifyStatus } from './composables/useSpotifyStatus'

const route = useRoute()
const router = useRouter()
const { startWatching, handleReturn } = useSpotifyStatus()

onMounted(async () => {
  startWatching()
  // The backend's OAuth callback sends us back with ?spotify=reconnected|error.
  // Read it once, then drop it so a reload doesn't replay the notice.
  await router.isReady()
  const { spotify, reason, ...rest } = route.query
  if (spotify) {
    handleReturn(spotify, reason)
    router.replace({ query: rest })
  }
})
</script>

<template>
  <header class="app-header">
    <router-link to="/" class="title-link">
      <h1>Spotify Podcast Tracker</h1>
    </router-link>
    <nav class="app-nav">
      <router-link to="/">Home</router-link>
      <span class="sep">·</span>
      <router-link :to="{ name: 'library', query: lastLibraryQuery }">Library</router-link>
      <span class="sep">·</span>
      <router-link to="/dashboard">Dashboard</router-link>
    </nav>
  </header>
  <main class="app-main">
    <SpotifyAuthBanner />
    <router-view />
  </main>
</template>

<style scoped>
.app-header {
  text-align: center;
}

/* The one place pages get their side margin; views only set vertical spacing. */
.app-main {
  padding-inline: var(--page-gutter);
}

.title-link {
  text-decoration: none;
  color: inherit;
}

.app-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
  font-size: 16px;
}

.app-nav a {
  text-decoration: none;
  color: var(--text);
  padding: 4px 10px;
  border-radius: 6px;
}

.app-nav a.router-link-exact-active {
  color: var(--text-h);
  background: var(--accent-bg);
  font-weight: 500;
}

.sep {
  color: var(--text);
  opacity: 0.5;
}
</style>
