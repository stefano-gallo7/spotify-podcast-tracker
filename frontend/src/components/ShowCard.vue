<script setup>
import { computed } from 'vue'

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

const lastPlayedLabel = computed(() => {
  if (!props.show.last_played_at) return null
  const date = new Date(props.show.last_played_at)
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
})
</script>

<template>
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
</template>

<style scoped>
.show-card {
  display: flex;
  gap: 16px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
  margin-left: 10px;
  margin-right: 10px;
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
