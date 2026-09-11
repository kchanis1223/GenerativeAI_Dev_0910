import type { TmsRow, TmsState } from '../types/tms'

/** CSV-only sample adapter for the existing TMS /orderList data shape. */
export function readCsv(source: string): Record<string, string>[] {
  const text = source.replace(/^\uFEFF/, '')
  const rows: string[][] = []
  let row: string[] = [],
    value = '',
    quoted = false,
    closed = false
  for (let i = 0; i < text.length; i++) {
    const char = text[i]!
    if (quoted) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          value += '"'
          i++
        } else {
          quoted = false
          closed = true
        }
      } else value += char
    } else if (char === '"') {
      if (value || closed) throw new Error('CSV 따옴표 위치가 올바르지 않습니다.')
      quoted = true
    } else if (char === ',') {
      row.push(value)
      value = ''
      closed = false
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && text[i + 1] === '\n') i++
      row.push(value)
      rows.push(row)
      row = []
      value = ''
      closed = false
    } else {
      if (closed) throw new Error('CSV 닫는 따옴표 뒤에 문자가 있습니다.')
      value += char
    }
  }
  if (quoted) throw new Error('CSV 따옴표가 닫히지 않았습니다.')
  if (row.length || value || closed) {
    row.push(value)
    rows.push(row)
  }
  const header = rows.shift()
  if (
    !header?.length ||
    header.some((key) => !key.trim()) ||
    new Set(header).size !== header.length
  )
    throw new Error('CSV 헤더가 없거나 중복되었습니다.')
  return rows.map((values, i) => {
    if (values.length !== header.length) throw new Error(`CSV ${i + 2}행의 컬럼 개수가 다릅니다.`)
    return Object.fromEntries(header.map((key, index) => [key, values[index]!]))
  })
}
const itemVehicleTypes: Record<string, string> = { 활어: '99', 냉장: '02', 냉동: '02', 일반: '01' }
const numericFields = [
  'latitude',
  'longitude',
  'deliveryWeight',
  'deliveryVolume',
  'serviceTime',
  'weight',
  'maxLoadKg',
  'volume',
  'skillPer',
  'endLatitude',
  'endLongitude',
  'seq',
]
function records(source: string, required: string[], id: string): TmsRow[] {
  const rows = readCsv(source)
  const ids = new Set<string>()
  return rows.map((row, index) => {
    for (const key of required)
      if (!row[key]?.trim()) throw new Error(`${index + 2}행: ${key} 값이 필요합니다.`)
    if (ids.has(row[id]!)) throw new Error(`중복 ${id}: ${row[id]}`)
    ids.add(row[id]!)
    const result: TmsRow = { ...row }
    for (const key of numericFields) {
      if (row[key] === undefined || row[key] === '') continue
      const value = Number(row[key])
      if (!Number.isFinite(value)) throw new Error(`${index + 2}행: ${key}는 숫자여야 합니다.`)
      result[key] = value
    }
    if (
      'latitude' in result &&
      (!Number.isFinite(Number(result.latitude)) || Math.abs(Number(result.latitude)) > 90)
    )
      throw new Error('위도 범위 오류')
    if (
      'longitude' in result &&
      (!Number.isFinite(Number(result.longitude)) || Math.abs(Number(result.longitude)) > 180)
    )
      throw new Error('경도 범위 오류')
    return result
  })
}
export function readDeliveryOrdersCsv(source: string, deliveryDate?: string): TmsRow[] {
  const rows = records(
    source,
    [
      'orderId',
      'orderName',
      'address',
      'latitude',
      'longitude',
      'deliveryWeight',
      'vehicleType',
      'serviceTime',
      'deliveryDate',
      'branchId',
      'centerId',
      'itemType',
      'itemName',
      'desiredDeliveryTime',
      'openTime',
      'closeTime',
    ],
    'orderId',
  )
  for (const row of rows) {
    const time = String(row.desiredDeliveryTime)
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(time))
      throw new Error('납품 희망시간은 HH:mm 형식이어야 합니다.')
    const compact = time.replace(':', '')
    if (
      ![row.openTime, row.closeTime].every((t) => /^([01]\d|2[0-3])[0-5]\d$/.test(String(t))) ||
      String(row.openTime) > compact ||
      compact > String(row.closeTime)
    )
      throw new Error('납품 희망시간과 시간창이 맞지 않습니다.')
    const date = String(row.deliveryDate)
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
      new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date
    )
      throw new Error('배송일 형식을 확인하세요.')
    if (Number(row.deliveryWeight) <= 0 || Number(row.deliveryVolume ?? 0) < 0)
      throw new Error('배송 중량·부피를 확인하세요.')
    if (!Number.isInteger(row.serviceTime) || Number(row.serviceTime) < 0)
      throw new Error('작업 시간은 0 이상의 정수입니다.')
    const type = itemVehicleTypes[String(row.itemType)]
    if (!type || row.vehicleType !== type) throw new Error('품목과 TMS 차량 유형이 맞지 않습니다.')
  }
  return deliveryDate ? rows.filter((row) => row.deliveryDate === deliveryDate) : rows
}
export interface DeliveryCsvSources {
  centers: string
  branches: string
  vehicles: string
  orders: string
}
export function readDeliveryDataset(
  sources: DeliveryCsvSources,
  deliveryDate?: string,
): { state: TmsState; branches: TmsRow[] } {
  const centers = records(
    sources.centers,
    ['centerId', 'centerName', 'address', 'latitude', 'longitude'],
    'centerId',
  )
  const branches = records(
    sources.branches,
    ['branchId', 'branchName', 'centerId', 'address', 'latitude', 'longitude', 'zoneCode'],
    'branchId',
  )
  const vehicles = records(
    sources.vehicles,
    [
      'vehicleId',
      'vehicleName',
      'vehicleClass',
      'centerId',
      'weight',
      'maxLoadKg',
      'volume',
      'vehicleType',
      'supportedItemTypes',
      'zoneCode',
      'inputYn',
      'skillPer',
    ],
    'vehicleId',
  )
  const orders = readDeliveryOrdersCsv(sources.orders, deliveryDate)
  for (const row of [...branches, ...vehicles, ...orders])
    if (!centers.some((c) => c.centerId === row.centerId))
      throw new Error(`등록되지 않은 센터: ${row.centerId}`)
  for (const order of orders) {
    const branch = branches.find((b) => b.branchId === order.branchId)
    if (
      !branch ||
      ['address', 'latitude', 'longitude', 'centerId', 'zoneCode'].some(
        (key) => branch[key] !== order[key],
      )
    )
      throw new Error(`주문과 지점 정보 불일치: ${order.orderId}`)
  }
  for (const v of vehicles) {
    if (
      !Number.isInteger(v.weight) ||
      Number(v.weight) <= 0 ||
      Number(v.weight) * 1000 !== v.maxLoadKg ||
      Number(v.volume) < 0
    )
      throw new Error('차량 적재량의 ton·kg 단위를 확인하세요.')
    if (
      !['0', '1'].includes(String(v.inputYn)) ||
      !['01', '02', '99'].includes(String(v.vehicleType))
    )
      throw new Error('차량 유형·투입 여부를 확인하세요.')
  }
  const zones = [...new Set([...branches, ...vehicles].map((row) => String(row.zoneCode)))].map(
    (code, index) => ({ code, name: code === 'SEOUL' ? '서울 전역' : code, seq: index + 1 }),
  )
  const nextSeq =
    Math.max(0, ...[...centers, ...vehicles, ...orders].map((r) => Number(r.seq ?? 0))) + 1
  return { state: { centers, zones, vehicles, orders, banLines: [], jobs: {}, nextSeq }, branches }
}
