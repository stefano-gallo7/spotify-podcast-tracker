<script setup>
import { ref, onMounted, watch } from 'vue'
import ShowCard from './ShowCard.vue'

const shows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref(null)

const q = ref('')

let debounceTimer = null

async function loadShows() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    if (q.value) params.set('q', q.value)
    const url = `http://localhost:8000/api/shows?${params}`
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`)
    }
    const data = await response.json()
    shows.value = data.items
    total.value = data.total
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(loadShows)

watch(q, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadShows, 300)
})
</script>

<template>
  <div class="controls">
    <input
      v-model="q"
      type="search"
      placeholder="Search shows..."
      class="search-input"
    />
    <p v-if="!loading" class="count">
      {{ total }} show{{ total === 1 ? '' : 's' }}
    </p>
  </div>

  <p v-if="loading" class="status-line">Loading…</p>
  <p v-else-if="error" class="status-line error">Failed to load: {{ error }}</p>
  <div v-else class="shows-list">
    <ShowCard v-for="show in shows" :key="show.id" :show="show" />
  </div>
</template>

<style scoped>
.controls {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 10px;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  font-size: 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  font-family: var(--sans);
}

.count {
  margin: 0;
  font-size: 14px;
  color: var(--text);
  white-space: nowrap;
}

.status-line {
  padding: 0 10px;
  color: var(--text);
}

.status-line.error {
  color: tomato;
}

.shows-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
