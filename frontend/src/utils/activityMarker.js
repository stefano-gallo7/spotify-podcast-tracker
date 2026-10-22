// Locate a date on the Activity chart's bucketed x-axis.
//
// Buckets are "YYYY-MM" (monthly) or week-start Monday "YYYY-MM-DD" (weekly);
// the resolution is inferred from the label shape, so a stale resolution can
// never be paired with fresh points. Returns { index, frac } — the bucket the
// date falls in and how far through it (0..1) — or null if it's outside the
// window. Dates are parsed by parts: `new Date("YYYY-MM-DD")` is UTC and can
// land a day early in local time.

function pad(n) {
  return String(n).padStart(2, '0')
}

export function markerPosition(points, dateStr) {
  if (!dateStr || !points.length) return null
  const [y, m, d] = dateStr.split('-').map(Number)
  const weekly = points[0].bucket.length === 10

  let label, frac
  if (weekly) {
    const date = new Date(y, m - 1, d)
    const dow = (date.getDay() + 6) % 7 // Monday = 0
    const monday = new Date(y, m - 1, d - dow)
    label = `${monday.getFullYear()}-${pad(monday.getMonth() + 1)}-${pad(monday.getDate())}`
    frac = dow / 7
  } else {
    const daysInMonth = new Date(y, m, 0).getDate()
    label = `${y}-${pad(m)}`
    frac = (d - 1) / daysInMonth
  }

  const index = points.findIndex((p) => p.bucket === label)
  return index === -1 ? null : { index, frac }
}
