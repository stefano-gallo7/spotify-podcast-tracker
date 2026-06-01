<script setup>
import { ref, onMounted, watch } from 'vue'
import ShowCard from './ShowCard.vue'

const shows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref(null)

const q = ref('')
const status = ref('')
const hasMore = ref(false)
const isFavorite = ref(false)
const sort = ref('name')
const order = ref('asc')

let debounceTimer = null

async function loadShows() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    if (q.value) params.set('q', q.value)
    if (status.value) params.set('status', status.value)
    if (hasMore.value) params.set('has_more', 'true')
    if (isFavorite.value) params.set('is_favorite', 'true')
    params.set('sort', sort.value)
    params.set('order', order.value)
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

function toggleOrder() {
  order.value = order.value === 'asc' ? 'desc' : 'asc'
}

onMounted(loadShows)

watch(q, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadShows, 300)
})

watch([status, hasMore, isFavorite, sort, order], loadShows)
</script>

<template>
  <div class="controls">
    <div class="search-row">
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

    <div class="filter-row">
      <select v-model="status">
        <option value="">All statuses</option>
        <option value="active">Active</option>
        <option value="finished">Finished</option>
        <option value="dropped">Dropped</option>
        <option value="paused">Paused</option>
      </select>

      <label class="checkbox-label">
        <input type="checkbox" v-model="hasMore" />
        Unheard episodes
      </label>

      <label class="checkbox-label">
        <input type="checkbox" v-model="isFavorite" />
        Favorites only
      </label>

      <div class="sort-controls">
        <span class="sort-label">Sort:</span>
        <select v-model="sort">
          <option value="name">Name</option>
          <option value="listened_count">Listened count</option>
          <option value="total_episodes">Total episodes</option>
          <option value="last_played">Last played</option>
        </select>
        <button
          type="button"
          class="order-button"
          :title="order === 'asc' ? 'Ascending' : 'Descending'"
          @click="toggleOrder"
        >
          {{ order === 'asc' ? '↑' : '↓' }}
        </button>
      </div>
    </div>
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
  flex-direction: column;
  gap: 10px;
  padding: 12px 10px;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  font-size: 14px;
}

.search-input,
select {
  padding: 8px 12px;
  font-size: 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  font-family: var(--sans);
}

.search-input {
  flex: 1;
}

select {
  font-size: 14px;
  padding: 6px 8px;
}

.count {
  margin: 0;
  font-size: 14px;
  color: var(--text);
  white-space: nowrap;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text);
  cursor: pointer;
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.sort-label {
  color: var(--text);
}

.order-button {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  cursor: pointer;
  font-size: 16px;
}

.order-button:hover {
  border-color: var(--accent);
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
