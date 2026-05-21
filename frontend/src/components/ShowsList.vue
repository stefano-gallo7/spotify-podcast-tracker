<script setup>
import { ref, onMounted } from 'vue'
import ShowCard from './ShowCard.vue'

const shows = ref([])
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const response = await fetch('http://localhost:8000/api/shows')
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`)
    }
    const data = await response.json()
    shows.value = data.items
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <p v-if="loading">Loading…</p>
  <p v-else-if="error">Failed to load shows: {{ error }}</p>
  <div v-else class="shows-list">
    <ShowCard v-for="show in shows" :key="show.id" :show="show" />
  </div>
</template>

<style scoped>
.shows-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
