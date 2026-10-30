<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import ShowTile from './ShowTile.vue'

// One Home section of show covers, in one of two shapes:
//   grid — wraps, capped to `rows` full rows, with an in-place Show all / less
//   row  — a single horizontal scroller with ‹ › buttons and a "See all →" end tile
const props = defineProps({
  title: { type: String, required: true },
  shows: { type: Array, required: true },
  total: { type: Number, default: null }, // full count when `shows` is a capped fetch
  variant: { type: String, default: 'grid' }, // 'grid' | 'row'
  rows: { type: Number, default: 2 }, // grid only
  seeAllTo: { type: [String, Object], default: null }, // row only
  emptyText: { type: String, default: 'Nothing here yet.' },
})

const count = computed(() => props.total ?? props.shows.length)

// Grid and scroller share one element ref; a ResizeObserver keeps the grid's
// column count (for the row cap) and the scroller's arrow states current.
const trackEl = ref(null)

// --- grid: cap to N full rows ---------------------------------------------
// The cap is counted in rows, not items, so the last visible row is never
// half-empty whatever the width. The column count is read from the rendered
// grid (auto-fill decides it), then the list is sliced — so hidden tiles
// aren't in the DOM (not tabbable), and we know whether a toggle is needed.
const columns = ref(1)
const expanded = ref(false)
const cap = computed(() => columns.value * props.rows)
const visibleShows = computed(() =>
  props.variant === 'grid' && !expanded.value ? props.shows.slice(0, cap.value) : props.shows,
)
const canExpand = computed(() => props.variant === 'grid' && props.shows.length > cap.value)

function measureColumns(el) {
  const tracks = getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean)
  columns.value = Math.max(1, tracks.length)
}

// --- row: arrow buttons (mouse wheels don't scroll sideways) ---------------
const canPrev = ref(false)
const canNext = ref(false)

function updateArrows() {
  const el = trackEl.value
  if (!el) return
  canPrev.value = el.scrollLeft > 1
  canNext.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 1
}

function scrollPage(direction) {
  const el = trackEl.value
  if (el) el.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: 'smooth' })
}

const observer = new ResizeObserver(() => {
  const el = trackEl.value
  if (!el) return
  if (props.variant === 'grid') measureColumns(el)
  else updateArrows()
})

// The track only exists when there are shows, so (un)observe as it comes and goes.
watch(trackEl, (el, old) => {
  if (old) observer.unobserve(old)
  if (el) observer.observe(el)
})

onBeforeUnmount(() => observer.disconnect())
</script>

<template>
  <section class="shelf" :class="`is-${variant}`">
    <header class="shelf-header">
      <h2>{{ title }} <span class="count">{{ count }}</span></h2>
      <div v-if="variant === 'row' && (canPrev || canNext)" class="arrows">
        <button type="button" aria-label="Scroll left" :disabled="!canPrev" @click="scrollPage(-1)">‹</button>
        <button type="button" aria-label="Scroll right" :disabled="!canNext" @click="scrollPage(1)">›</button>
      </div>
    </header>

    <p v-if="!shows.length" class="empty">{{ emptyText }}</p>

    <template v-else-if="variant === 'grid'">
      <div ref="trackEl" class="grid">
        <ShowTile v-for="show in visibleShows" :key="show.id" :show="show" />
      </div>
      <button v-if="canExpand || expanded" type="button" class="toggle" @click="expanded = !expanded">
        {{ expanded ? 'Show less' : `Show all ${shows.length}` }}
      </button>
    </template>

    <div v-else ref="trackEl" class="scroller" @scroll.passive="updateArrows">
      <ShowTile v-for="show in shows" :key="show.id" :show="show" size="small" class="item" />
      <router-link v-if="seeAllTo" :to="seeAllTo" class="item see-all">
        <span class="see-all-box">See all {{ count }} →</span>
      </router-link>
    </div>
  </section>
</template>

<style scoped>
.shelf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.shelf-header h2 {
  margin: 0;
}

.count {
  margin-left: 8px;
  font-size: 16px;
  font-weight: 400;
  color: var(--text);
}

.is-row .shelf-header h2 {
  font-size: 20px;
}

.empty {
  color: var(--text);
  font-size: 14px;
}

/* --- grid --- */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 20px 16px;
}

.toggle {
  display: block;
  margin: 16px auto 0;
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  font-family: var(--sans);
  font-size: 14px;
  cursor: pointer;
}

.toggle:hover {
  border-color: var(--accent);
}

/* --- row --- */
.scroller {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  scroll-snap-type: x proximity;
  scrollbar-width: thin;
  /* room for the tile hover lift, which overflow would otherwise clip */
  padding: 4px 0 8px;
}

.item {
  flex: 0 0 120px;
  scroll-snap-align: start;
}

.see-all {
  text-decoration: none;
}

.see-all-box {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1;
  padding: 8px;
  text-align: center;
  border: 1px dashed var(--border);
  border-radius: 8px;
  color: var(--accent);
  font-size: 14px;
  transition: border-color 0.15s;
}

.see-all:hover .see-all-box,
.see-all:focus-visible .see-all-box {
  border-color: var(--accent);
}

.arrows {
  display: flex;
  gap: 6px;
}

.arrows button {
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--bg);
  color: var(--text-h);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.arrows button:hover:not(:disabled) {
  border-color: var(--accent);
}

.arrows button:disabled {
  opacity: 0.35;
  cursor: default;
}
</style>
