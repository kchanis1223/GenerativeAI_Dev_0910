export const routeColors = ['#008c8d', '#7962ca', '#d18426', '#3580b9', '#d26272']
export const number = (value: number) => value.toLocaleString('ko-KR', { maximumFractionDigits: 1 })
export const duration = (seconds: number) => {
  const pad = (v: number) => String(v).padStart(2, '0')
  return `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor((seconds % 3600) / 60))}:${pad(Math.floor(seconds % 60))}`
}
export const arrival = (value: string) =>
  /^\d{12}$/.test(value) ? `${value.slice(8, 10)}:${value.slice(10, 12)}` : '—'
