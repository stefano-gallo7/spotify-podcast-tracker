// Register only the Chart.js pieces the dashboard uses, so the bundle stays
// lean. Side-effect import: `import '../charts/register.js'` in each chart
// component (idempotent — Chart.register can be called repeatedly).
import {
  Chart,
  DoughnutController,
  ArcElement,
  BarController,
  BarElement,
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js'

Chart.register(
  DoughnutController,
  ArcElement,
  BarController,
  BarElement,
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
)
