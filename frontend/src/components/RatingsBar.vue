<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { useChartTheme } from '../composables/useChartTheme.js'
import { axisBarOptions } from '../charts/options.js'
import '../charts/register.js'

const props = defineProps({
  data: { type: Array, required: true }, // [{ rating, count }]
})

const theme = useChartTheme()

const chartData = computed(() => ({
  labels: props.data.map((d) => '★'.repeat(d.rating)),
  datasets: [
    {
      data: props.data.map((d) => d.count),
      backgroundColor: theme.value.sequential,
      borderRadius: 4,
      borderSkipped: false,
    },
  ],
}))

const options = computed(() => {
  const o = axisBarOptions(theme.value, { horizontal: false })
  o.scales.y.ticks.precision = 0
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
  height: 260px;
}
</style>
