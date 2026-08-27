<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getStatsOverview, getTopShows, getActivity, getStatsByTag } from '../api.js'
import { formatHours } from '../utils/format.js'
import StatTile from '../components/StatTile.vue'
import StatusDonut from '../components/StatusDonut.vue'
import RatingsBar from '../components/RatingsBar.vue'
import TopShowsBar from '../components/TopShowsBar.vue'
import ActivityLine from '../components/ActivityLine.vue'
import TagBreakdown from '../components/TagBreakdown.vue'
import SegmentedControl from '../components/SegmentedControl.vue'

const overview = ref(null)
const topShows = ref([])
const activity = ref({ points: [], has_older: false, has_newer: false, start: null, end: null })
const tags = ref([])
const loading = ref(true)
const error = ref(null)

const topShowsBy = ref('hours')
const tagsBy = ref('hours')
const METRIC_OPTS = [
  { label: 'Hours', value: 'hours' },
  { label: 'Episodes', value: 'episodes' },
]

const activityMetric = ref('episodes')
const activityResolution = ref('month')
const activityMonths = ref(12)
// Window end anchored this many months back from now; paging shifts it, but
// changing resolution / window length leaves it put (the end stays fixed).
const activityEndOffset = ref(0)
// Weekly over "All" is too noisy to be useful — disable it there and fall back
// to monthly, remembering the weekly preference for the shorter windows.
const effectiveResolution = computed(() =>
  activityMonths.value === 0 ? 'month' : activityResolution.value,
)
const resolutionModel = computed({
  get: () => effectiveResolution.value,
  set: (v) => {
    activityResolution.value = v
  },
})
const resOptions = computed(() => [
  { label: 'Monthly', value: 'month' },
  { label: 'Weekly', value: 'week', disabled: activityMonths.value === 0 },
])
const WINDOW_OPTS = [
  { label: '3m', value: 3 },
  { label: '6m', value: 6 },
  { label: '12m', value: 12 },
  { label: 'All', value: 0 },
]

const H = 3600000

onMounted(async () => {
  try {
    const [ov, top, act, byTag] = await Promise.all([
      getStatsOverview(),
      getTopShows({ limit: 10, by: topShowsBy.value }),
      getActivity({ months: activityMonths.value, resolution: effectiveResolution.value }),
      getStatsByTag({ by: tagsBy.value }),
    ])
    overview.value = ov
    topShows.value = top
    activity.value = act
    tags.value = byTag
  } catch (e) {
    error.value = 'Failed to load dashboard.'
  } finally {
    loading.value = false
  }
})

// Toggle → refetch (the server re-ranks / re-filters per metric). Keep the
// existing chart on a failed refetch rather than blanking it.
watch(topShowsBy, async (by) => {
  try {
    topShows.value = await getTopShows({ limit: 10, by })
  } catch (e) {
    /* keep current data */
  }
})

watch(tagsBy, async (by) => {
  try {
    tags.value = await getStatsByTag({ by })
  } catch (e) {
    /* keep current data */
  }
})

// Metric is a pure client-side prop swap. Resolution/window/paging change the
// fetched window, so they refetch — but the end stays anchored, so changing
// resolution or window length does NOT reset the paging position.
async function loadActivity() {
  try {
    activity.value = await getActivity({
      months: activityMonths.value,
      resolution: effectiveResolution.value,
      endOffset: activityEndOffset.value,
    })
  } catch (e) {
    /* keep current data */
  }
}
watch([effectiveResolution, activityMonths], loadActivity)
function pageOlder() {
  if (activity.value.has_older) {
    activityEndOffset.value += activityMonths.value
    loadActivity()
  }
}
function pageNewer() {
  if (activity.value.has_newer) {
    activityEndOffset.value = Math.max(0, activityEndOffset.value - activityMonths.value)
    loadActivity()
  }
}

const tiles = computed(() => {
  const o = overview.value
  if (!o) return []
  const measuredH = Math.round(o.measured_ms_played / H)
  const fromLengthH = Math.round((o.estimated_ms_played - o.measured_ms_played) / H)
  return [
    {
      label: 'Shows',
      value: o.total_shows,
      sub: o.favorite_shows ? `♥ ${o.favorite_shows} favorites` : null,
    },
    { label: 'Episodes played', 
      value: o.episodes_played,
      sub: `${o.episodes_in_progress} in progress`,
     },
    {
      label: 'Listening time',
      value: formatHours(o.estimated_ms_played),
      sub: `${measuredH}h measured + ${fromLengthH}h from length`,
    },
    {
      label: 'Avg rating',
      value: o.average_rating != null ? o.average_rating.toFixed(1) : '—',
      sub: `${o.rated_count} episodes rated`,
    },
  ]
})

const hasRatings = computed(() => overview.value && overview.value.rated_count > 0)

function monthToDate(ym) {
  const [y, m] = ym.split('-').map(Number)
  return new Date(y, m - 1, 1)
}
const activityRange = computed(() => {
  const a = activity.value
  if (!a.start || !a.end) return ''
  const s = monthToDate(a.start)
  const e = monthToDate(a.end)
  const sM = s.toLocaleDateString(undefined, { month: 'short' })
  const eM = e.toLocaleDateString(undefined, { month: 'short' })
  if (s.getFullYear() === e.getFullYear()) return `${sM}–${eM} ${e.getFullYear()}`
  return `${sM} ${s.getFullYear()} – ${eM} ${e.getFullYear()}`
})
</script>

<template>
  <main class="dashboard">
    <h2>Dashboard</h2>

    <p v-if="loading" class="status">Loading…</p>
    <p v-else-if="error" class="status error">{{ error }}</p>

    <template v-else>
      <section class="tiles">
        <StatTile
          v-for="tile in tiles"
          :key="tile.label"
          :label="tile.label"
          :value="tile.value"
          :sub="tile.sub"
        />
      </section>

      <section class="charts">
        <div class="chart-card">
          <h3>Shows by status</h3>
          <StatusDonut :data="overview.status_breakdown" />
        </div>
        
        <div class="chart-card wide">
          <div class="card-head">
            <h3>Top shows <span class="cap">by {{topShowsBy}} listened</span></h3>
            <SegmentedControl v-model="topShowsBy" :options="METRIC_OPTS" />
          </div>
          <TopShowsBar :data="topShows" :metric="topShowsBy" />
        </div>
        
        <div class="chart-card full">
          <div class="card-head">
            <h3>Activity <span class="cap">by last-played · approximate</span></h3>
            <div class="head-controls">
              <div v-if="activityMonths !== 0" class="period-nav">
                <button class="nav-arrow" :disabled="!activity.has_older" aria-label="Older" @click="pageOlder">‹</button>
                <span class="period-label">{{ activityRange }}</span>
                <button class="nav-arrow" :disabled="!activity.has_newer" aria-label="Newer" @click="pageNewer">›</button>
              </div>
              <SegmentedControl v-model="activityMetric" :options="METRIC_OPTS" />
              <SegmentedControl v-model="resolutionModel" :options="resOptions" />
              <SegmentedControl v-model="activityMonths" :options="WINDOW_OPTS" />
            </div>
          </div>
          <ActivityLine :data="activity.points" :metric="activityMetric" />
        </div>
        
        <div v-if="hasRatings" class="chart-card">
          <h3>Ratings</h3>
          <RatingsBar :data="overview.ratings_distribution" />
        </div>

        <div v-if="tags.length" class="chart-card full">
          <div class="card-head">
            <h3>By tag <span class="cap">by {{tagsBy}} listened</span></h3>
            <SegmentedControl v-model="tagsBy" :options="METRIC_OPTS" />
          </div>
          <TagBreakdown :data="tags" :metric="tagsBy" />
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.dashboard {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px 40px;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}

.charts {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

/* ≥700px: two equal columns */
@media (min-width: 700px) {
  .charts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* ≥1000px: three columns — the donut keeps column 1, the bar chart takes 2–3 */
@media (min-width: 1000px) {
  .charts {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .chart-card.wide {
    grid-column: span 2;
  }
}

.chart-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: var(--shadow);
  min-width: 0;
  overflow-x: auto;
}

.chart-card.full {
  grid-column: 1 / -1;
}

.chart-card h3 {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-h);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.card-head h3 {
  margin: 0;
}

.head-controls {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.period-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-arrow {
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  border-radius: 6px;
  width: 24px;
  height: 24px;
  line-height: 1;
  font-size: 15px;
  cursor: pointer;
}

.nav-arrow:hover:not(:disabled) {
  color: var(--text-h);
  background: var(--accent-bg);
}

.nav-arrow:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.period-label {
  font-size: 12px;
  color: var(--text);
  min-width: 96px;
  text-align: center;
}

.cap {
  font-weight: 400;
  font-size: 12px;
  color: var(--text);
  opacity: 0.7;
}

.status {
  padding: 40px 0;
  text-align: center;
  color: var(--text);
}

.status.error {
  color: #e5484d;
}
</style>
