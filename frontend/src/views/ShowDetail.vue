<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { formatDate } from '../utils/format'
import { getShow } from '../api'

const route = useRoute()

const show = ref(null)
const loading = ref(true)
const error = ref(null)

const progress = computed(() => {
  if (!show.value?.total_episodes) return null
  return `${show.value.listened_count} of ${show.value.total_episodes} episodes`
})

async function loadShow() {
  loading.value = true
  error.value = null
  try {
    show.value = await getShow(route.params.id)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(loadShow)
</script>

<template>
  <div class="page">
    <router-link to="/" class="back-link">← Back to library</router-link>

    <p v-if="loading" class="status-line">Loading…</p>
    <p v-else-if="error" class="status-line error">Failed to load: {{ error }}</p>

    <article v-else-if="show" class="show-detail">
      <header class="show-header">
        <img
          v-if="show.image_url_big"
          :src="show.image_url_big"
          :alt="`Cover for ${show.name}`"
          class="cover"
        />
        <div class="info">
          <h2>
            {{ show.name }}
            <span v-if="show.is_favorite" class="favorite" aria-label="Favorite">★</span>
          </h2>
          <p v-if="progress" class="meta">{{ progress }}</p>
          <p class="meta status">{{ show.status }}</p>
          <a
            v-if="show.spotify_url"
            :href="show.spotify_url"
            target="_blank"
            rel="noopener"
            class="spotify-link"
          >Open in Spotify ↗</a>
        </div>
      </header>

      <section v-if="show.description" class="description" v-html="show.description"></section>

      <section class="episodes">
        <h3>Episodes ({{ show.episodes.length }})</h3>
        <ul>
          <li v-for="episode in show.episodes" :key="episode.uri" class="episode">
            <span class="ep-played" :class="{ done: episode.is_fully_played }">
              {{ episode.is_fully_played ? '✓' : '·' }}
            </span>
            <span class="ep-name">{{ episode.name }}</span>
            <span v-if="formatDate(episode.release_date)" class="ep-date">
              {{ formatDate(episode.release_date) }}
            </span>
          </li>
        </ul>
      </section>
    </article>
  </div>
</template>

<style scoped>
.page {
  padding: 12px 10px;
  max-width: 900px;
  margin: 0 auto;
}

.back-link {
  display: inline-block;
  margin-bottom: 16px;
  color: var(--accent);
  text-decoration: none;
  font-size: 14px;
}

.back-link:hover {
  text-decoration: underline;
}

.status-line {
  color: var(--text);
}

.status-line.error {
  color: tomato;
}

.show-header {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}

.cover {
  width: 200px;
  height: 200px;
  object-fit: cover;
  border-radius: 8px;
  flex-shrink: 0;
}

.info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.info h2 {
  margin: 0;
  color: var(--text-h);
}

.favorite {
  color: var(--accent);
  margin-left: 6px;
}

.meta {
  margin: 0;
  font-size: 14px;
  color: var(--text);
}

.status {
  text-transform: capitalize;
  color: var(--accent);
  font-size: 12px;
}

.spotify-link {
  margin-top: 8px;
  color: var(--accent);
  text-decoration: none;
  font-size: 14px;
}

.spotify-link:hover {
  text-decoration: underline;
}

.description {
  font-size: 15px;
  color: var(--text);
  margin-bottom: 24px;
  line-height: 1.5;
}

.description :deep(p) {
  margin: 0 0 8px;
}

.episodes h3 {
  margin: 0 0 12px;
  font-size: 18px;
  color: var(--text-h);
  font-weight: 500;
}

.episodes ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.episode {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}

.ep-played {
  flex-shrink: 0;
  width: 16px;
  color: var(--text);
  font-weight: bold;
}

.ep-played.done {
  color: var(--accent);
}

.ep-name {
  flex: 1;
  color: var(--text-h);
}

.ep-date {
  flex-shrink: 0;
  color: var(--text);
  white-space: nowrap;
}
</style>
