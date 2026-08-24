<script setup>
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { useChartTheme } from '../composables/useChartTheme.js'
import '../charts/register.js'

const props = defineProps({
  data: { type: Array, required: true }, // [{ status, count }]
})

const theme = useChartTheme()

// Fixed status → categorical slot, so a status keeps its color even when
// another drops to zero (color follows the entity, never its rank/order).
const STATUS_ORDER = ['active', 'finished', 'paused', 'dropped']
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1)

const chartData = computed(() => {
  const map = Object.fromEntries(props.data.map((d) => [d.status, d.count]))
  const present = STATUS_ORDER.filter((s) => (map[s] ?? 0) > 0)
  const slot = Object.fromEntries(STATUS_ORDER.map((s, i) => [s, i]))
  return {
    labels: present.map(cap),
    datasets: [
      {
        data: present.map((s) => map[s]),
        backgroundColor: present.map((s) => theme.value.categorical[slot[s]]),
        borderColor: theme.value.surface, // 2px surface ring between slices
        borderWidth: 2,
      },
    ],
  }
})

const options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '58%',
  plugins: {
    legend: {
      position: 'right',
      labels: { color: theme.value.muted, usePointStyle: true, boxWidth: 10, boxHeight: 10 },
    },
  },
}))
</script>

<template>
  <div class="chart-box">
    <Doughnut :data="chartData" :options="options" />
  </div>
</template>

<style scoped>
.chart-box {
  position: relative;
  height: 260px;
}
</style>
