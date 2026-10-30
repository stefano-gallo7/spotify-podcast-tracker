<script setup>
import { formatHours } from '../utils/format'

// Compact strip of in-progress episodes (EpisodeDetail objects, parent show
// embedded). The parent decides visibility — Home hides this when empty.
defineProps({
  episodes: { type: Array, required: true },
})

function progressPct(ep) {
  if (!ep.duration_ms) return null
  return Math.min(100, Math.round((ep.resume_position_ms / ep.duration_ms) * 100))
}

function timeLeft(ep) {
  if (!ep.duration_ms) return null
  const remaining = ep.duration_ms - ep.resume_position_ms
  // formatHours rounds to whole minutes, which would read "0m left" here.
  return remaining < 60000 ? '<1m left' : `${formatHours(remaining)} left`
}
</script>

<template>
  <section class="continue">
    <h2>Continue listening</h2>
    <div class="list">
      <router-link
        v-for="ep in episodes"
        :key="ep.uri"
        :to="{ name: 'show-detail', params: { id: ep.show.id } }"
        class="ep"
        :title="`${ep.name} — ${ep.show.name}`"
      >
        <img
          v-if="ep.image_url_medium || ep.show.image_url_small"
          :src="ep.image_url_medium || ep.show.image_url_small"
          alt=""
          class="thumb"
          loading="lazy"
        />
        <div class="body">
          <span class="ep-name">{{ ep.name }}</span>
          <span class="show-name">{{ ep.show.name }}</span>
          <div v-if="progressPct(ep) !== null" class="progress-row">
            <div
              class="bar"
              role="progressbar"
              :aria-valuenow="progressPct(ep)"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div class="fill" :style="{ width: `${progressPct(ep)}%` }" />
            </div>
            <span class="left">{{ timeLeft(ep) }}</span>
          </div>
        </div>
      </router-link>
    </div>
  </section>
</template>

<style scoped>
.continue h2 {
  font-size: 20px;
  margin-bottom: 12px;
}

.list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}

.ep {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  min-width: 0;
  transition: border-color 0.15s;
}

.ep:hover,
.ep:focus-visible {
  border-color: var(--accent);
}

.thumb {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.ep-name,
.show-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ep-name {
  font-size: 14px;
  color: var(--text-h);
}

.show-name {
  font-size: 12px;
  color: var(--text);
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.bar {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: var(--border);
  overflow: hidden;
}

.fill {
  height: 100%;
  background: var(--accent);
}

.left {
  font-size: 12px;
  color: var(--text);
  white-space: nowrap;
}
</style>
