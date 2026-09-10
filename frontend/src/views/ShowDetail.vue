<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createPatchHelper } from '../utils/applyPatch'
import { getShow, updateShow } from '../api'
import EpisodeRow from '../components/EpisodeRow.vue'
import TagChips from '../components/TagChips.vue'

const route = useRoute()

const show = ref(null)
const loading = ref(true)
const error = ref(null)

const notes = ref('')

const applyPatch = createPatchHelper({
  getter: () => show.value,
  setter: (v) => { show.value = v },
  update: updateShow,
})

const progress = computed(() => {
  if (!show.value?.total_episodes) return null
  return `${show.value.listened_count} of ${show.value.total_episodes} episodes`
})

const isNotesDirty = computed(
  () => show.value && notes.value !== (show.value.notes ?? '')
)

async function loadShow() {
  loading.value = true
  error.value = null
  try {
    show.value = await getShow(route.params.id)
    notes.value = show.value.notes ?? ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  await applyPatch({ is_favorite: !show.value.is_favorite })
}

async function onStatusChange(event) {
  const newStatus = event.target.value
  if (newStatus !== show.value.status) {
    await applyPatch({ status: newStatus })
  }
}

async function saveNotes() {
  if (!isNotesDirty.value) return
  await applyPatch({ notes: notes.value.trim() || null })
  notes.value = show.value.notes ?? ''
}

function onEpisodeUpdate(updated) {
  if (!show.value) return
  const i = show.value.episodes.findIndex((e) => e.uri === updated.uri)
  if (i !== -1) {
    show.value.episodes[i] = updated
  }
}

// Keep the local notes ref in sync when the server response replaces show.value
watch(show, (s) => {
  if (s) notes.value = s.notes ?? ''
})

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
            <button
              type="button"
              class="favorite-btn"
              :class="{ active: show.is_favorite }"
              :aria-label="show.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
              :aria-pressed="show.is_favorite"
              @click="toggleFavorite"
            >
              {{ show.is_favorite ? '♥' : '♡' }}
            </button>
          </h2>
          <p v-if="progress" class="meta">{{ progress }}</p>
          <label class="status-control">
            <span class="status-label">Status:</span>
            <select :value="show.status" @change="onStatusChange">
              <option value="active">Active</option>
              <option value="finished">Finished</option>
              <option value="dropped">Dropped</option>
              <option value="paused">Paused</option>
            </select>
          </label>
          <a
            v-if="show.spotify_url"
            :href="show.spotify_url"
            target="_blank"
            rel="noopener"
            class="spotify-link"
          >Open in Spotify ↗</a>
          <TagChips :show="show" @update="show = $event" />
        </div>
      </header>

      <section v-if="show.description" class="description" v-html="show.description"></section>

      <section class="notes-section">
        <h3>Notes</h3>
        <textarea
          v-model="notes"
          placeholder="Add notes about this show..."
          rows="4"
          class="notes-input"
        ></textarea>
        <div class="notes-controls">
          <button
            type="button"
            class="save-btn"
            :disabled="!isNotesDirty"
            @click="saveNotes"
          >
            Save
          </button>
          <span v-if="isNotesDirty" class="dirty-marker">Unsaved changes</span>
        </div>
      </section>

      <section class="episodes">
        <h3>Episodes ({{ show.episodes.length }})</h3>
        <div class="episodes-header" aria-hidden="true">
          <span class="header-date">Release date</span>
        </div>
        <ul>
          <EpisodeRow
            v-for="episode in show.episodes"
            :key="episode.uri"
            :episode="episode"
            @update="onEpisodeUpdate"
          />
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
  gap: 8px;
  min-width: 0;
}

.info h2 {
  margin: 0;
  color: var(--text-h);
  display: flex;
  align-items: center;
  gap: 8px;
}

.favorite-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 24px;
  padding: 0;
  color: var(--text);
  transition: color 0.15s;
  font-family: inherit;
  line-height: 1;
}

.favorite-btn:hover {
  color: var(--accent);
}

.favorite-btn.active {
  color: var(--accent);
}

.meta {
  margin: 0;
  font-size: 14px;
  color: var(--text);
}

.status-control {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text);
}

.status-control select {
  padding: 4px 8px;
  font-size: 14px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg);
  color: var(--text-h);
  font-family: var(--sans);
}

.spotify-link {
  margin-top: 4px;
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

.notes-section {
  margin-bottom: 24px;
}

.notes-section h3 {
  margin: 0 0 12px;
  font-size: 18px;
  color: var(--text-h);
  font-weight: 500;
}

.notes-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  font-family: var(--sans);
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  resize: vertical;
  box-sizing: border-box;
}

.notes-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.save-btn {
  padding: 6px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  cursor: pointer;
  font-family: var(--sans);
  font-size: 14px;
}

.save-btn:hover:not(:disabled) {
  border-color: var(--accent);
}

.save-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dirty-marker {
  font-size: 13px;
  color: var(--accent);
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

.episodes-header {
  display: flex;
  justify-content: flex-end;
  padding: 0 0 6px;
  border-bottom: 1px solid var(--border);
  font-size: 10px;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.header-date {
  width: 90px;
  text-align: center;
}
</style>
