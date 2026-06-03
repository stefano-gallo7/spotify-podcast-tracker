<template>
  <header class="app-header">
    <router-link to="/" class="title-link">
      <h1>Spotify Podcast Tracker</h1>
    </router-link>
  </header>
  <router-view />
</template>

<style scoped>
.app-header {
  text-align: center;
}

.title-link {
  text-decoration: none;
  color: inherit;
}
</style>
