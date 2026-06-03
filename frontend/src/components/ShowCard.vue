<script setup>
import { computed } from 'vue'
import { formatDate } from '../utils/format'

const props = defineProps({
  show: {
    type: Object,
    required: true,
  },
})

const progress = computed(() => {
  if (!props.show.total_episodes) return null
  return `${props.show.listened_count} of ${props.show.total_episodes} episodes`
})

const lastPlayedLabel = computed(() => formatDate(props.show.last_played_at))
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
          <span v-if="show.is_favorite" class="favorite" aria-label="Favorite">★</span>
        </h3>
        <p v-if="progress" class="meta">{{ progress }}</p>
        <p v-if="lastPlayedLabel" class="meta">Last played: {{ lastPlayedLabel }}</p>
        <p class="meta status">{{ show.status }}</p>
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
}

.info h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: var(--text-h);
}

.favorite {
  color: var(--accent);
  font-size: 16px;
  margin-left: 6px;
}

.meta {
  margin: 0;
  font-size: 14px;
  color: var(--text);
}

.status {
  text-transform: capitalize;
  font-size: 12px;
  color: var(--accent);
}
</style>
