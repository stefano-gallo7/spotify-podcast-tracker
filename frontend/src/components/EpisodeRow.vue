<script setup>
import { ref } from 'vue'
import { createPatchHelper } from '../utils/applyPatch'
import { updateEpisode } from '../api'
import { formatDate } from '../utils/format'

const props = defineProps({
  episode: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update'])

const applyPatch = createPatchHelper({
  getter: () => props.episode,
  setter: (v) => emit('update', v),
  update: updateEpisode,
})

const hoverRating = ref(0)

function setRating(n) {
  const newRating = props.episode.rating === n ? null : n
  applyPatch({ rating: newRating })
}

function toggleFavorite() {
  return applyPatch({ is_favorite: !props.episode.is_favorite })
}
</script>

<template>
  <li class="episode-row">
    <span class="ep-played" :class="{ done: episode.is_fully_played }">
      {{ episode.is_fully_played ? '✓' : '·' }}
    </span>
    <span class="ep-name">{{ episode.name }}</span>
    
    <div class="actions">
      <div
        class="rating"
        role="radiogroup"
        aria-label="Rating"
        @mouseleave="hoverRating = 0"
      >
        <button
          v-for="n in 5"
          :key="n"
          type="button"
          class="star-btn"
          :class="{ filled: n <= (hoverRating || (episode.rating ?? 0)) }"
          :aria-label="`${n} star${n > 1 ? 's' : ''}`"
          @mouseenter="hoverRating = n"
          @click="setRating(n)"
        >
          ★
        </button>
      </div>
      <button
        type="button"
        class="favorite-btn"
        :class="{ active: episode.is_favorite }"
        :aria-label="episode.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
        :aria-pressed="episode.is_favorite"
        @click="toggleFavorite"
      >
        {{ episode.is_favorite ? '♥' : '♡' }}
      </button>
    </div>
    <span v-if="formatDate(episode.release_date)" class="ep-date">
      {{ formatDate(episode.release_date) }}
    </span>
    <!-- <span v-if="formatDate(episode.last_played_at)" class="ep-date">
      {{ formatDate(episode.last_played_at) }}
    </span> -->
  </li>
</template>

<style scoped>
.episode-row {
  display: flex;
  align-items: center;
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
  text-align: center;
}

.ep-played.done {
  color: var(--accent);
}

.ep-name {
  flex: 1;
  color: var(--text-h);
  min-width: 0;
}

.ep-date {
  flex-shrink: 0;
  color: var(--text);
  white-space: nowrap;
  font-size: 13px;
  width: 90px;
  text-align: right;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.rating {
  display: flex;
}

.star-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 0 1px;
  color: var(--border);
  transition: color 0.1s;
  line-height: 1;
  font-family: inherit;
}

.star-btn.filled {
  color: var(--accent);
}

.favorite-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
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
</style>
