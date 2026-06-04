<script setup>
import { computed } from 'vue'
import { formatDate } from '../utils/format'
import { createPatchHelper } from '../utils/applyPatch'
import { updateShow } from '../api'

const props = defineProps({
  show: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update'])

const applyPatch = createPatchHelper({
  getter: () => props.show,
  setter: (v) => emit('update', v),
  update: updateShow,
})

const progress = computed(() => {
  if (!props.show.total_episodes) return null
  return `${props.show.listened_count} of ${props.show.total_episodes} episodes`
})

const lastPlayedLabel = computed(() => formatDate(props.show.last_played_at))

function toggleFavorite() {
  return applyPatch({ is_favorite: !props.show.is_favorite })
}

function onStatusChange(event) {
  const newStatus = event.target.value
  if (newStatus !== props.show.status) {
    applyPatch({ status: newStatus })
  }
}
</script>

<template>
  <router-link
    :to="{ name: 'show-detail', params: { id: show.id } }"
    class="card-link"
  >
    <article class="show-card">
      <img
        v-if="show.image_url_medium"
        :src="show.image_url_medium"
        :alt="`Cover for ${show.name}`"
        class="cover"
      />
      <div class="info">
        <h3>
          {{ show.name }}
          <button
            type="button"
            class="favorite-btn"
            :class="{ active: show.is_favorite }"
            :aria-label="show.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
            :aria-pressed="show.is_favorite"
            @click.prevent.stop="toggleFavorite"
          >
            {{ show.is_favorite ? '★' : '☆' }}
          </button>
        </h3>
        <p v-if="progress" class="meta">{{ progress }}</p>
        <p v-if="lastPlayedLabel" class="meta">Last played: {{ lastPlayedLabel }}</p>
        <select
          class="status-select"
          :value="show.status"
          @click.stop
          @mousedown.stop
          @change="onStatusChange"
        >
          <option value="active">Active</option>
          <option value="finished">Finished</option>
          <option value="dropped">Dropped</option>
          <option value="paused">Paused</option>
        </select>
      </div>
    </article>
  </router-link>
</template>

<style scoped>
.card-link {
  display: block;
  text-decoration: none;
  color: inherit;
  margin-left: 10px;
  margin-right: 10px;
}

.show-card {
  display: flex;
  gap: 16px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
  transition: border-color 0.15s;
}

.card-link:hover .show-card {
  border-color: var(--accent);
}

.cover {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}

.info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  align-items: flex-start;
}

.info h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: var(--text-h);
  display: flex;
  align-items: center;
  gap: 6px;
}

.favorite-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
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

.status-select {
  margin-top: 2px;
  padding: 2px 6px;
  font-size: 12px;
  font-family: var(--sans);
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg);
  color: var(--accent);
  text-transform: capitalize;
  cursor: pointer;
}

.status-select:hover {
  border-color: var(--accent);
}
</style>
