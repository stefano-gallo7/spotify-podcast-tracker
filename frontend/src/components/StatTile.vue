<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  sub: { type: String, default: null },
})
</script>

<template>
  <div class="stat-tile">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }}</div>
    <div v-if="sub" class="stat-sub">{{ sub }}</div>
  </div>
</template>

<style scoped>
.stat-tile {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: var(--shadow);
}

.stat-value {
  margin-top: 10px;
  font-size: 32px;
  font-weight: 600;
  color: var(--text-h);
  line-height: 1.1;
  letter-spacing: -0.5px;
}

.stat-label {
  margin-top: 0px;
  font-size: 16px;
  color: var(--text);
}

.stat-sub {
  margin-top: 12px;
  font-size: 14px;
  color: var(--text);
  opacity: 0.75;
}
</style>
