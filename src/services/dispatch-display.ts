export const routeColors = ['#3D97B4', '#7962ca', '#d18426', '#0F7088', '#d26272']
export const number = (value: number) => value.toLocaleString('ko-KR', { maximumFractionDigits: 1 })
export const duration = (seconds: number | null) => {
  if (seconds === null) return '미제공'
  const pad = (v: number) => String(v).padStart(2, '0')
  return `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor((seconds % 3600) / 60))}:${pad(Math.floor(seconds % 60))}`
}
export const arrival = (value: string) =>
  /^\d{12}$/.test(value)
    ? `${value.slice(8, 10)}:${value.slice(10, 12)}`
    : value && !Number.isNaN(Date.parse(value))
      ? value.slice(11, 16)
      : '미제공'
