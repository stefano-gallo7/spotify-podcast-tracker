<script setup>
// Cover-first, read-only show tile for Home's shelves. Deliberately has no
// inline controls (unlike ShowCard) — editing happens in the detail view.
defineProps({
  show: { type: Object, required: true },
  size: { type: String, default: 'large' }, // 'large' | 'small'
})
</script>

<template>
  <router-link
    :to="{ name: 'show-detail', params: { id: show.id } }"
    class="show-tile"
    :class="size"
    :title="show.name"
  >
    <div class="cover-wrap">
      <img
        v-if="show.image_url_medium"
        :src="show.image_url_medium"
        :alt="`Cover for ${show.name}`"
        class="cover"
        loading="lazy"
      />
      <div v-else class="cover placeholder" aria-hidden="true">
        {{ show.name.charAt(0) }}
      </div>
      <span v-if="show.is_favorite" class="fav-badge" aria-label="Favorite">♥</span>
    </div>
    <span class="name">{{ show.name }}</span>
  </router-link>
</template>

<style scoped>
.show-tile {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  text-decoration: none;
  color: inherit;
}

.cover-wrap {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
  transition: border-color 0.15s, transform 0.15s;
}

.show-tile:hover .cover-wrap,
.show-tile:focus-visible .cover-wrap {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-bg);
  color: var(--accent);
  font-size: 40px;
  font-weight: 600;
}

.fav-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 13px;
  line-height: 1;
}

/* Two lines max, then ellipsis — the full name is in the tooltip. */
.name {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 15px;
  line-height: 1.3;
  color: var(--text-h);
}

.large .name {
  font-weight: 600;
}

.small .name {
  font-size: 13px;
}

.small .placeholder {
  font-size: 28px;
}
</style>
