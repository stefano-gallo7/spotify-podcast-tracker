<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { useChartTheme } from '../composables/useChartTheme.js'
import { axisBarOptions } from '../charts/options.js'
import { formatHours } from '../utils/format.js'
import '../charts/register.js'

// Magnitude ranking by tag → single hue (not per-tag categorical, which would
// colour by rank once sorted). Rendered only when tags exist (parent gates it).
const props = defineProps({
  data: { type: Array, required: true }, // [{ tag, shows, episodes_played, estimated_ms_played }]
  metric: { type: String, default: 'hours' }, // 'hours' | 'episodes'
})

const theme = useChartTheme()

const chartData = computed(() => ({
  labels: props.data.map((t) => t.tag),
  datasets: [
    {
      data: props.data.map((t) =>
        props.metric === 'hours' ? t.estimated_ms_played / 3600000 : t.episodes_played,
      ),
      backgroundColor: theme.value.sequential,
      borderRadius: 4,
      borderSkipped: false,
    },
  ],
}))

const options = computed(() => {
  const o = axisBarOptions(theme.value, { horizontal: true })
  o.scales.y.ticks.autoSkip = false
  o.plugins.tooltip = {
    callbacks: {
      label: (ctx) =>
        props.metric === 'hours'
          ? formatHours(props.data[ctx.dataIndex].estimated_ms_played)
          : `${props.data[ctx.dataIndex].episodes_played} episodes`,
    },
  }
  return o
})
</script>

<template>
  <div class="chart-box">
    <Bar :data="chartData" :options="options" />
  </div>
</template>

<style scoped>
.chart-box {
  position: relative;
  height: 300px;
}
</style>
