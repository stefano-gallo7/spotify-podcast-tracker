import { ref, onMounted, onUnmounted } from 'vue'

// Categorical hues (identity) and the single sequential hue (magnitude), from
// the validated dataviz reference palette. Dark = the same hues re-stepped for
// the dark surface. Validated against this app's surfaces (#fff / #16171d):
// light worst adjacent CVD ΔE 9.1, dark 8.4 — both above the 8 target.
const CATEGORICAL = {
  light: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'],
  dark: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'],
}
const SEQUENTIAL = { light: '#2a78d6', dark: '#3987e5' }

function readVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

// Chart.js can't read CSS variables, so pull the app's theme tokens at build
// time and hand them to the chart options. `mode` follows the OS setting — the
// app themes via prefers-color-scheme, with no in-app toggle.
function buildTheme() {
  const dark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const mode = dark ? 'dark' : 'light'
  return {
    mode,
    ink: readVar('--text-h', dark ? '#f3f4f6' : '#08060d'),
    muted: readVar('--text', dark ? '#9ca3af' : '#6b6375'),
    grid: readVar('--border', dark ? '#2e303a' : '#e5e4e7'),
    surface: readVar('--bg', dark ? '#16171d' : '#ffffff'),
    categorical: CATEGORICAL[mode],
    sequential: SEQUENTIAL[mode],
  }
}

// Reactive theme that rebuilds when the OS light/dark preference flips.
export function useChartTheme() {
  const theme = ref(buildTheme())
  const mql = window.matchMedia('(prefers-color-scheme: dark)')
  const update = () => {
    theme.value = buildTheme()
  }
  onMounted(() => mql.addEventListener('change', update))
  onUnmounted(() => mql.removeEventListener('change', update))
  return theme
}
