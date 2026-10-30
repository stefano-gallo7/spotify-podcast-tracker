<script setup>
import { ref, computed, onMounted } from 'vue'
import { listShows, listEpisodes, getActivity, getStatsOverview } from '../api'
import { formatHours } from '../utils/format'
import ContinueListening from '../components/ContinueListening.vue'
import ShowShelf from '../components/ShowShelf.vue'
import StatTile from '../components/StatTile.vue'

const ACTIVE_LIMIT = 100 // the list route's max — fetch every active show so "Show all" is instant
const ROW_LIMIT = 12 // paused / finished scrollers; the rest is one "See all →" away
const CONTINUE_LIMIT = 6

const active = ref({ items: [], total: 0 })
const paused = ref({ items: [], total: 0 })
const finished = ref({ items: [], total: 0 })
const inProgress = ref([])
const thisMonth = ref(null) // { episodes, estimated_ms } or null
const finishedThisYear = ref(0)
const loading = ref(true)
const error = ref(null)

function byLastPlayed(status, limit) {
  return listShows({ status, sort: 'last_played', order: 'desc', limit })
}

onMounted(async () => {
  try {
    const [act, pau, fin, eps, month, overview] = await Promise.all([
      byLastPlayed('active', ACTIVE_LIMIT),
      byLastPlayed('paused', ROW_LIMIT),
      byLastPlayed('finished', ROW_LIMIT),
      listEpisodes({ inProgress: true, showStatus: 'active', limit: CONTINUE_LIMIT }),
      getActivity({ months: 1 }),
      getStatsOverview(),
    ])
    active.value = act
    paused.value = pau
    finished.value = fin
    inProgress.value = eps
    thisMonth.value = month.points.at(-1) ?? null
    finishedThisYear.value = overview.shows_finished_this_year
  } catch (e) {
    error.value = 'Failed to load home.'
  } finally {
    loading.value = false
  }
})

// Approximate: Activity buckets each episode once, by its *latest* play, so a
// replayed episode only counts in the month it was last heard.
const monthTile = computed(() => {
  const m = thisMonth.value ?? { episodes: 0, estimated_ms: 0 }
  return {
    value: m.episodes,
    sub: `~${formatHours(m.estimated_ms)} · approximate`,
  }
})

const shelfSummary = computed(
  () => `${paused.value.total} paused · ${finished.value.total} finished`,
)
</script>

<template>
  <div class="home">
    <p v-if="loading" class="status-line">Loading…</p>
    <p v-else-if="error" class="status-line error">{{ error }}</p>

    <template v-else>
      <div class="kpis">
        <StatTile label="Active shows" :value="active.total" :sub="shelfSummary" />
        <StatTile
          label="Episodes this month"
          :value="monthTile.value"
          :sub="monthTile.sub"
          title="Counts episodes whose most recent play falls in this month — a replayed episode counts only in the month it was last heard."
        />
        <StatTile
          label="Finished this year"
          :value="finishedThisYear"
          :sub="`of ${finished.total} finished`"
          title="Finished shows whose last episode was played this year."
        />
      </div>

      <ContinueListening v-if="inProgress.length" :episodes="inProgress" />

      <ShowShelf
        title="Active"
        :shows="active.items"
        :total="active.total"
        variant="grid"
        :rows="2"
        empty-text="No active shows."
      />

      <ShowShelf
        title="Paused"
        :shows="paused.items"
        :total="paused.total"
        variant="row"
        :see-all-to="{ name: 'library', query: { status: 'paused' } }"
        empty-text="No paused shows."
      />

      <ShowShelf
        title="Finished"
        :shows="finished.items"
        :total="finished.total"
        variant="row"
        :see-all-to="{ name: 'library', query: { status: 'finished' } }"
        empty-text="No finished shows yet."
      />
    </template>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 40px;
  padding-bottom: 40px;
}

/* Fixed-width tiles, centred as a group; they wrap on narrow screens. */
.kpis {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 16px;
}

.kpis > * {
  flex: 0 1 240px;
}

.status-line {
  color: var(--text);
}

.status-line.error {
  color: tomato;
}
</style>
