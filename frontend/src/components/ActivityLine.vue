<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart } from 'chart.js'
import { useChartTheme } from '../composables/useChartTheme.js'
import { lineOptions } from '../charts/options.js'
import { formatHours } from '../utils/format.js'
import { markerPosition } from '../utils/activityMarker.js'
import '../charts/register.js'

const props = defineProps({
  data: { type: Array, required: true }, // [{ bucket, episodes, estimated_ms }]
  metric: { type: String, default: 'episodes' }, // 'episodes' | 'hours'
  marker: { type: String, default: null }, // "YYYY-MM-DD" to mark, or null
})

const theme = useChartTheme()

// Dashed vertical reference line where the imported export's data ends. Drawn
// behind the dataset. vue-chartjs binds `plugins` once at chart creation, so
// this reads its position from the (reactive) options — never from a closure.
const historyLinePlugin = {
  id: 'historyLine',
  beforeDatasetsDraw(chart, _args, opts) {
    if (opts.index == null) return
    const { ctx, chartArea, scales: { x } } = chart
    const n = chart.data.labels.length
    const x0 = x.getPixelForValue(opts.index)
    // Interpolate toward the next bucket; past the last one, extrapolate the spacing.
    let x1 = x0
    if (opts.index + 1 < n) x1 = x.getPixelForValue(opts.index + 1)
    else if (opts.index > 0) x1 = x0 + (x0 - x.getPixelForValue(opts.index - 1))
    const px = Math.min(Math.max(x0 + opts.frac * (x1 - x0), chartArea.left), chartArea.right)

    ctx.save()
    ctx.strokeStyle = opts.color
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])
    ctx.beginPath()
    ctx.moveTo(px, chartArea.top)
    ctx.lineTo(px, chartArea.bottom)
    ctx.stroke()

    // Label sits in the top padding, flipped left near the right edge.
    ctx.setLineDash([])
    ctx.fillStyle = opts.color
    ctx.font = `11px ${Chart.defaults.font.family}`
    ctx.textBaseline = 'bottom'
    const flip = px > chartArea.right - 120
    ctx.textAlign = flip ? 'right' : 'left'
    ctx.fillText(opts.label, px + (flip ? -4 : 4), chartArea.top - 2)
    ctx.restore()
  },
}

const markerPos = computed(() => markerPosition(props.data, props.marker))

const markerLabel = computed(() => {
  if (!props.marker) return ''
  const [y, m, d] = props.marker.split('-').map(Number)
  const date = new Date(y, m - 1, d).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  return `export ends · ${date}`
})

const chartData = computed(() => ({
  labels: props.data.map((p) => p.bucket),
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
  const pos = markerPos.value
  o.plugins.historyLine = pos
    ? { index: pos.index, frac: pos.frac, color: theme.value.muted, label: markerLabel.value }
    : { index: null }
  // Room for the marker label above the plot, only when it's drawn.
  if (pos) o.layout = { padding: { top: 16 } }
  return o
})
</script>

<template>
  <div class="chart-box">
    <Line :data="chartData" :options="options" :plugins="[historyLinePlugin]" />
  </div>
</template>

<style scoped>
.chart-box {
  position: relative;
  height: 260px;
}
</style>
