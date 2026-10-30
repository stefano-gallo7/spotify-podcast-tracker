<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ShowCard from '../components/ShowCard.vue'
import AddShowModal from '../components/AddShowModal.vue'
import { listShows } from '../api'

const PAGE_SIZE = 20
const STATUSES = ['active', 'finished', 'dropped', 'paused']
const SORT_KEYS = ['name', 'listened_count', 'total_episodes', 'last_played']
const DEFAULT_SORT = 'last_played'
const DEFAULT_ORDER = 'desc'

const route = useRoute()
const router = useRouter()

const shows = ref([])
const total = ref(0)
const offset = ref(0)
const loading = ref(false)
const error = ref(null)

const q = ref('')
const status = ref('')
const hasMore = ref(false)
const isFavorite = ref(false)
const sort = ref(DEFAULT_SORT)
const order = ref(DEFAULT_ORDER)

// Filter state lives in the URL (?q=&status=&has_more=&is_favorite=&sort=&order=)
// so links like Home's "See all →" land pre-filtered and reloads keep the view.
// Unknown values fall back to defaults; defaults are left out of the URL.
function readQuery(query) {
  q.value = typeof query.q === 'string' ? query.q : ''
  status.value = STATUSES.includes(query.status) ? query.status : ''
  hasMore.value = query.has_more === 'true'
  isFavorite.value = query.is_favorite === 'true'
  sort.value = SORT_KEYS.includes(query.sort) ? query.sort : DEFAULT_SORT
  order.value = query.order === 'asc' ? 'asc' : DEFAULT_ORDER
}

function writeQuery() {
  const query = {}
  if (q.value) query.q = q.value
  if (status.value) query.status = status.value
  if (hasMore.value) query.has_more = 'true'
  if (isFavorite.value) query.is_favorite = 'true'
  if (sort.value !== DEFAULT_SORT) query.sort = sort.value
  if (order.value !== DEFAULT_ORDER) query.order = order.value
  // replace, not push: filter tweaks shouldn't pile up Back-button entries.
  router.replace({ query })
}

// Before the watchers below exist, so the initial read doesn't trigger them.
readQuery(route.query)

const isAddOpen = ref(false)
const addButton = ref(null)

function closeAddModal() {
  addButton.value?.focus() // Return focus to the button that opened the modal, after it unmounts.
  isAddOpen.value = false
}

let debounceTimer = null

const currentPage = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const canPrev = computed(() => offset.value > 0)
const canNext = computed(() => offset.value + PAGE_SIZE < total.value)

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
    params.set('limit', PAGE_SIZE)
    params.set('offset', offset.value)
    const data = await listShows(params)
    shows.value = data.items
    total.value = data.total
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// Sort isn't a filter, so it survives a clear.
const hasActiveFilters = computed(
  () => Boolean(q.value || status.value || hasMore.value || isFavorite.value),
)

function clearFilters() {
  q.value = ''
  status.value = ''
  hasMore.value = false
  isFavorite.value = false
}

function toggleOrder() {
  order.value = order.value === 'asc' ? 'desc' : 'asc'
}

function nextPage() {
  offset.value += PAGE_SIZE
  loadShows()
}

function prevPage() {
  offset.value = Math.max(0, offset.value - PAGE_SIZE)
  loadShows()
}

function onShowUpdate(updated) {
  const index = shows.value.findIndex((s) => s.id === updated.id)
  if (index !== -1) {
    shows.value[index] = updated
  }
}

function onShowAdded(show) {
  shows.value.unshift(show)
  total.value += 1
}

onMounted(loadShows)

watch(q, () => {
  offset.value = 0
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    writeQuery()
    loadShows()
  }, 300)
})

watch([status, hasMore, isFavorite, sort, order], () => {
  offset.value = 0
  writeQuery()
  loadShows()
})

// The URL can change while Library stays mounted (e.g. clicking "Library" in
// the nav from /library?status=paused). Re-read it; our own writeQuery()
// echoes back here too, but sets every ref to its current value — a no-op.
// Guarded on the route name: when navigating away the query empties before
// unmount, and resetting the filters then would fire a replace() mid-navigation.
watch(
  () => route.query,
  (query) => {
    if (route.name === 'library') readQuery(query)
  },
)
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
      <button
        ref="addButton"
        type="button"
        class="add-button"
        title="Add a show"
        aria-label="Add a show"
        @click="isAddOpen = true">
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
          <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
        </svg>
      </button>
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

      <button v-if="hasActiveFilters" type="button" class="clear-filters" @click="clearFilters">
        Clear filters
      </button>

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
  <template v-else>
    <div class="shows-list">
      <ShowCard
        v-for="show in shows"
        :key="show.id"
        :show="show"
        @update="onShowUpdate"
      />
    </div>
    <div v-if="total > 0" class="pagination">
      <button type="button" :disabled="!canPrev" @click="prevPage">← Prev</button>
      <span class="page-indicator">Page {{ currentPage }} of {{ totalPages }}</span>
      <button type="button" :disabled="!canNext" @click="nextPage">Next →</button>
    </div>
  </template>
  <AddShowModal v-if="isAddOpen" @close="closeAddModal" @added="onShowAdded" />
</template>

<style scoped>
.controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 0;
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

.clear-filters {
  padding: 0;
  border: none;
  background: none;
  color: var(--accent);
  font-family: var(--sans);
  font-size: 14px;
  cursor: pointer;
}

.clear-filters:hover {
  text-decoration: underline;
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

.add-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  cursor: pointer;
}

.add-button:hover {
  border-color: var(--accent);
}

.status-line {
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

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px 0;
}

.pagination button {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  font-family: var(--sans);
  font-size: 14px;
  cursor: pointer;
}

.pagination button:hover:not(:disabled) {
  border-color: var(--accent);
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-indicator {
  font-size: 14px;
  color: var(--text);
  min-width: 100px;
  text-align: center;
}
</style>
