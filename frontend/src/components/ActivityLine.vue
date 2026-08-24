<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import { useChartTheme } from '../composables/useChartTheme.js'
import { lineOptions } from '../charts/options.js'
import { formatHours } from '../utils/format.js'
import '../charts/register.js'

const props = defineProps({
  data: { type: Array, required: true }, // [{ month, episodes, estimated_ms }]
  metric: { type: String, default: 'episodes' }, // 'episodes' | 'hours'
})

const theme = useChartTheme()

const chartData = computed(() => ({
  labels: props.data.map((p) => p.month),
  datasets: [
    {
      data: props.data.map((p) =>
        props.metric === 'hours' ? p.estimated_ms / 3600000 : p.episodes,
      ),
      borderColor: theme.value.sequential,
      backgroundColor: theme.value.sequential,
      fill: false,
    },
  ],
}))

const options = computed(() => {
  const o = lineOptions(theme.value)
  o.plugins.tooltip = {
    callbacks: {
      label: (ctx) =>
        props.metric === 'hours'
          ? formatHours(props.data[ctx.dataIndex].estimated_ms)
          : `${props.data[ctx.dataIndex].episodes} episodes`,
    },
  }
  return o
})
</script>

<template>
  <div class="chart-box">
    <Line :data="chartData" :options="options" />
  </div>
</template>

<style scoped>
.chart-box {
  position: relative;
  height: 260px;
}
</style>
