<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { searchSpotifyShows, addShowByUri } from '../api'

const emit = defineEmits(['close', 'added'])

const q = ref('')
const results = ref([])
const loading = ref(false)
const error = ref(null)
const adding = ref(null) // uri currently being added
const highlight = ref(null) // index of the keyboard-active row

const searchInput = ref(null)
const resultsList = ref(null)

let debounceTimer = null

watch(q, () => {
  clearTimeout(debounceTimer)
  const term = q.value.trim()
  if (!term) {
    results.value = []
    error.value = null
    loading.value = false
    return
  }
  loading.value = true
  debounceTimer = setTimeout(runSearch, 300)
})

async function runSearch() {
  const term = q.value.trim()
  if (!term) return
  loading.value = true
  error.value = null
  try {
    results.value = await searchSpotifyShows(term)
    highlight.value = null // nothing highlighted until the user arrows or hovers
  } catch (err) {
    error.value = err.message
    results.value = []
  } finally {
    loading.value = false
  }
}

async function add(result) {
  if (result.already_in_library || adding.value) return
  adding.value = result.uri
  try {
    const show = await addShowByUri(result.uri)
    emit('added', show)
    emit('close')
  } catch (err) {
    error.value = err.message
  } finally {
    adding.value = null
  }
}

function scrollHighlightIntoView() {
  nextTick(() => {
    resultsList.value?.children[highlight.value]?.scrollIntoView({ block: 'nearest' })
  })
}

// Ignore hover events that fire without the pointer actually moving (i.e. when
// the list scrolls under a stationary cursor) so keyboard nav isn't hijacked.
let lastPointer = { x: null, y: null }

function onHover(e, index) {
  if (e.clientX === lastPointer.x && e.clientY === lastPointer.y) return
  lastPointer = { x: e.clientX, y: e.clientY }
  highlight.value = index
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault() // stop the native "clear search input" behavior on empty field
    e.stopPropagation()
    emit('close')
    return
  }
  if (!results.value.length) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    highlight.value = highlight.value === null
      ? 0
      : Math.min(highlight.value + 1, results.value.length - 1)
    scrollHighlightIntoView()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    highlight.value = highlight.value === null
      ? 0
      : Math.max(highlight.value - 1, 0)
    scrollHighlightIntoView()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (highlight.value !== null) add(results.value[highlight.value])
  }
}

onMounted(() => {
  searchInput.value?.focus()
})
</script>

<template>
  <div class="backdrop" @click="emit('close')">
    <div class="modal" @click.stop>
      <input
        ref="searchInput"
        v-model="q"
        type="search"
        placeholder="Search Spotify…"
        class="search-input"
        @keydown="onKeydown"
      />

      <p v-if="loading" class="status-line">Searching…</p>
      <p v-else-if="error" class="status-line error">{{ error }}</p>
      <p v-else-if="q.trim() && results.length === 0" class="status-line">No results.</p>

      <ul v-else ref="resultsList" class="results">
        <li
          v-for="(result, index) in results"
          :key="result.uri"
          class="result"
          :class="{ disabled: result.already_in_library, highlighted: index === highlight }"
          @click="add(result)"
          @mousemove="onHover($event, index)"
        >
          <img
            v-if="result.image_url_small"
            :src="result.image_url_small"
            :alt="`Cover for ${result.name}`"
            class="thumb"
          />
          <div v-else class="thumb placeholder">{{ result.name.charAt(0) }}</div>

          <div class="info">
            <span class="name">{{ result.name }}</span>
            <span v-if="result.description_excerpt" class="excerpt">
              {{ result.description_excerpt }}
            </span>
          </div>

          <button
            type="button"
            class="add-btn"
            :disabled="result.already_in_library || adding === result.uri"
            @click.stop="add(result)"
          >
            <template v-if="result.already_in_library">In library</template>
            <template v-else-if="adding === result.uri">Adding…</template>
            <template v-else>Add</template>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 10vh;
  z-index: 100;
}

.modal {
  width: 100%;
  max-width: 520px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  overflow: hidden;
}

.search-input {
  padding: 10px 12px;
  font-size: 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  font-family: var(--sans);
}

.status-line {
  margin: 0;
  padding: 8px 4px;
  color: var(--text);
}

.status-line.error {
  color: tomato;
}

.results {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
}

.result {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.result.highlighted:not(.disabled) {
  background: rgba(144, 144, 144, 0.181);
}

.result.disabled {
  cursor: default;
  opacity: 0.6;
}

.thumb {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  object-fit: cover;
  border-radius: 4px;
}

.thumb.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--border);
  color: var(--text-h);
  font-weight: 600;
  text-transform: uppercase;
}

.info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.name {
  font-weight: 600;
  color: var(--text-h);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.excerpt {
  font-size: 13px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.add-btn {
  flex-shrink: 0;
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  font-family: var(--sans);
  font-size: 14px;
  cursor: pointer;
}

.add-btn:hover:not(:disabled) {
  border-color: var(--accent);
}

.add-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
