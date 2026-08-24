<template>
  <header class="app-header">
    <router-link to="/" class="title-link">
      <h1>Spotify Podcast Tracker</h1>
    </router-link>
    <nav class="app-nav">
      <router-link to="/">Library</router-link>
      <span class="sep">·</span>
      <router-link to="/dashboard">Dashboard</router-link>
    </nav>
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

.app-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
  font-size: 16px;
}

.app-nav a {
  text-decoration: none;
  color: var(--text);
  padding: 4px 10px;
  border-radius: 6px;
}

.app-nav a.router-link-exact-active {
  color: var(--text-h);
  background: var(--accent-bg);
  font-weight: 500;
}

.sep {
  color: var(--text);
  opacity: 0.5;
}
</style>
