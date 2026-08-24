// Shared Chart.js option builders. Each takes the current theme so colors track
// light/dark. Marks follow the dataviz specs: recessive grid/axes (value axis
// only, no ticks, no border), no legend on single-series charts, 4px rounded
// bar ends, 2px lines, ≥8px markers.

export function axisBarOptions(theme, { horizontal = false } = {}) {
  const valueGrid = { color: theme.grid, drawTicks: false }
  const catGrid = { display: false }
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? 'y' : 'x',
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: {
        grid: horizontal ? valueGrid : catGrid,
        border: { display: false },
        ticks: { color: theme.muted },
        beginAtZero: true,
      },
      y: {
        grid: horizontal ? catGrid : valueGrid,
        border: { display: false },
        ticks: { color: theme.muted },
        beginAtZero: true,
      },
    },
  }
}

export function lineOptions(theme) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { display: false },
        ticks: { color: theme.muted, maxRotation: 0, autoSkipPadding: 12 },
      },
      y: {
        grid: { color: theme.grid, drawTicks: false },
        border: { display: false },
        ticks: { color: theme.muted },
        beginAtZero: true,
      },
    },
    elements: {
      line: { borderWidth: 2, tension: 0.25 },
      point: { radius: 3, hoverRadius: 5 },
    },
  }
}
