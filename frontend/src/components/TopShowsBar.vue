<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { useChartTheme } from '../composables/useChartTheme.js'
import { axisBarOptions } from '../charts/options.js'
import { formatHours } from '../utils/format.js'
import '../charts/register.js'

const props = defineProps({
  data: { type: Array, required: true }, // [{ id, name, estimated_ms_played, listened_count }]
  metric: { type: String, default: 'hours' }, // 'hours' | 'episodes'
})

const theme = useChartTheme()

const chartData = computed(() => ({
  labels: props.data.map((s) => s.name),
  datasets: [
    {
      data: props.data.map((s) =>
        props.metric === 'hours' ? s.estimated_ms_played / 3600000 : s.listened_count,
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
  o.scales.y.ticks.font = { size: 11 }
  // Truncate long show names on the category axis.
  o.scales.y.ticks.callback = function (value) {
    const label = this.getLabelForValue(value)
    return label.length > 26 ? label.slice(0, 25) + '…' : label
  }
  o.plugins.tooltip = {
    callbacks: {
      title: (items) => props.data[items[0].dataIndex].name,
      label: (ctx) =>
        props.metric === 'hours'
          ? formatHours(props.data[ctx.dataIndex].estimated_ms_played)
          : `${props.data[ctx.dataIndex].listened_count} episodes`,
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
  height: 340px;
}
</style>
