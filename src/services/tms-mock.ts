import catalogJson from '../data/tms-api-catalog.json'
import { newOrder, newVehicle, resources } from '../data/logistics'
import type {
  ApiOperation,
  DispatchResult,
  Resource,
  TmsPayload,
  TmsRow,
  TmsState,
  VehiclePlan,
} from '../types/tms'

export const apiCatalog = catalogJson as ApiOperation[]
export const vehicleTypes = { '01': '상온', '02': '냉장·냉동', '99': '기타' } as const
export class TmsError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message)
    this.name = 'TmsError'
  }
}
const fail = (message: string, code = '400'): never => {
  throw new TmsError(code, message)
}
const n = (row: TmsPayload, key: string) => Number(row[key] ?? 0)
const text = (row: TmsPayload, key: string) => String(row[key] ?? '')
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value))
const stamp = (now: number) => new Date(now).toLocaleString('sv-SE')
export const success = (resultData?: TmsRow[]) =>
  resultData
    ? {
        resultCode: '200',
        resultCount: resultData.length,
        resultMessage: 'success',
        resultData: clone(resultData),
      }
    : { resultCode: '200', resultCount: 0, resultMessage: '성공적으로 반영 되었습니다.' }

const numericFields = new Set([
  'latitude',
  'longitude',
  'endLatitude',
  'endLongitude',
  'weight',
  'volume',
  'skillPer',
  'serviceTime',
  'deliveryWeight',
  'deliveryVolume',
  'seq',
])
function normalizedPayload(input: TmsPayload): TmsPayload {
  const result: TmsPayload = {}
  for (const [key, value] of Object.entries(input)) {
    if (value === undefined || value === null || (value === '' && numericFields.has(key))) continue
    if (numericFields.has(key)) {
      if (
        (typeof value !== 'number' && typeof value !== 'string') ||
        !Number.isFinite(Number(value))
      )
        fail(`${key}: 유효한 숫자를 입력하세요.`)
      result[key] = Number(value)
    } else result[key] = typeof value === 'string' ? value.trim() : value
  }
  return result
}
function validateParameters(operation: ApiOperation, input: TmsPayload) {
  for (const parameter of operation.parameters) {
    if (parameter.name === 'RAW_BODY' || parameter.name === 'reqDatas') continue
    const value = input[parameter.name]
    if (parameter.required && (value === undefined || value === ''))
      fail(`${parameter.name}: 필수 값입니다.`)
    if (
      value !== undefined &&
      parameter.type === 'string' &&
      !numericFields.has(parameter.name) &&
      typeof value !== 'string'
    )
      fail(`${parameter.name}: 문자열이어야 합니다.`)
    if (value !== undefined && parameter.type === 'int' && !Number.isInteger(value))
      fail(`${parameter.name}: 정수여야 합니다.`)
  }
}
function validateRecord(state: TmsState, resource: Resource, row: TmsRow) {
  const meta = resources[resource]
  if (
    resource !== 'banLines' &&
    (!String(row[meta.id] ?? '').trim() || String(row[meta.id]).length > 80)
  )
    fail('ID는 1~80자로 입력하세요.')
  if (resource === 'centers' || resource === 'orders') {
    if (
      !Number.isFinite(n(row, 'latitude')) ||
      Math.abs(n(row, 'latitude')) > 90 ||
      !Number.isFinite(n(row, 'longitude')) ||
      Math.abs(n(row, 'longitude')) > 180
    )
      fail('위도·경도 범위를 확인하세요.')
  }
  if (resource === 'vehicles' || resource === 'orders') {
    if (!['01', '02', '99'].includes(text(row, 'vehicleType')))
      fail('차량 유형은 01, 02, 99 중 하나입니다.')
    if (row.zoneCode && !state.zones.some((z) => z.code === row.zoneCode))
      fail('등록된 권역 코드를 선택하세요.')
    const weightKey = resource === 'vehicles' ? 'weight' : 'deliveryWeight'
    const volumeKey = resource === 'vehicles' ? 'volume' : 'deliveryVolume'
    if (n(row, weightKey) <= 0 || n(row, volumeKey) < 0)
      fail('무게는 0보다 커야 하며 부피는 음수일 수 없습니다.')
  }
  if (resource === 'vehicles') {
    if (!['0', '1'].includes(text(row, 'inputYn'))) fail('inputYn은 0 또는 1입니다.')
    if (n(row, 'skillPer') < 10 || n(row, 'skillPer') > 100 || n(row, 'skillPer') % 10 !== 0)
      fail('숙련도는 10~100 사이의 10 단위입니다.')
    if (Math.abs(n(row, 'endLatitude')) > 90 || Math.abs(n(row, 'endLongitude')) > 180)
      fail('차량 도착 좌표가 유효하지 않습니다.')
    if ((n(row, 'endLatitude') === 0) !== (n(row, 'endLongitude') === 0))
      fail('차량 도착 위도와 경도는 함께 입력하세요.')
  }
  if (
    resource === 'orders' &&
    (!Number.isInteger(n(row, 'serviceTime')) || n(row, 'serviceTime') < 0)
  )
    fail('서비스 시간은 0 이상의 정수(분)입니다.')
  if (resource === 'banLines') parseLine(text(row, 'lineData'))
}
function baseRow(resource: Resource, input: TmsPayload): TmsRow {
  if (resource === 'vehicles')
    return newVehicle(text(input, 'vehicleId'), text(input, 'vehicleName'), {
      zoneCode: '',
      volume: 0,
    })
  if (resource === 'orders')
    return newOrder(text(input, 'orderId'), text(input, 'orderName'), {
      zoneCode: '',
      address: '',
      deliveryVolume: 0,
    })
  if (resource === 'zones') return { code: '', name: '', zipcodeData: '', adminData: '' }
  if (resource === 'centers')
    return {
      centerId: '',
      centerName: text(input, 'centerId'),
      address: '',
      latitude: 0,
      longitude: 0,
    }
  return { lineName: '', lineData: '' }
}
function mutate(
  state: TmsState,
  operation: ApiOperation,
  resource: Resource,
  input: TmsPayload,
  now: number,
) {
  const meta = resources[resource]
  const key = meta.id
  if (operation.path.endsWith('Delete')) {
    let ids = [text(input, key)]
    if (resource === 'vehicles' || resource === 'orders') {
      if (!['1', '2'].includes(text(input, 'deleteFlag')))
        fail('deleteFlag는 전체 1, 선택 2입니다.')
      if (input.deleteFlag === '1') ids = state[resource].map((r) => String(r[key]))
      else
        ids = text(input, key)
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
      if (input.deleteFlag === '2' && !ids.length) fail('삭제할 ID를 지정하세요.')
    }
    if (ids.some((id) => !state[resource].some((r) => String(r[key]) === id)))
      fail('삭제할 항목을 찾을 수 없습니다.', '404')
    if (
      resource === 'zones' &&
      [...state.vehicles, ...state.orders].some((r) => ids.includes(text(r, 'zoneCode')))
    )
      fail('차량 또는 배송지에서 사용하는 권역입니다. 먼저 연결을 변경하세요.', '409')
    state[resource] = state[resource].filter((r) => !ids.includes(String(r[key])))
    return success()
  }
  const updating = operation.path.endsWith('Update')
  const index = state[resource].findIndex((r) => String(r[key]) === String(input[key]))
  if (updating && index < 0) fail('수정할 항목을 찾을 수 없습니다.', '404')
  if (!updating && resource !== 'banLines' && index >= 0) fail('이미 존재하는 ID입니다.', '409')
  const record = updating ? { ...state[resource][index]! } : baseRow(resource, input)
  // Only contract fields can be changed, so internal seq/state cannot be overwritten.
  for (const p of operation.parameters) {
    const value = input[p.name]
    if (value !== undefined && (typeof value === 'number' || typeof value === 'string'))
      record[p.name] = value
  }
  record.updateDate = stamp(now)
  if (!updating) record.seq = state.nextSeq
  validateRecord(state, resource, record)
  if (updating) state[resource][index] = record
  else {
    state[resource].push(record)
    state.nextSeq++
  }
  return success()
}

type Point = { latitude: number; longitude: number }
const point = (row: TmsPayload): Point => ({
  latitude: n(row, 'latitude'),
  longitude: n(row, 'longitude'),
})
export function distanceMeters(a: Point, b: Point): number {
  const rad = Math.PI / 180
  const dLat = (b.latitude - a.latitude) * rad,
    dLon = (b.longitude - a.longitude) * rad
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(a.latitude * rad) * Math.cos(b.latitude * rad) * Math.sin(dLon / 2) ** 2
  return Math.round(6371000 * 2 * Math.asin(Math.sqrt(Math.min(1, h))))
}
function parseLine(value: string): Point[] {
  const points = value.split('_').map((pair) => {
    const values = pair.split(',')
    if (values.length !== 2 || values.some((v) => !v.trim()))
      fail('교차금지선은 경도,위도_경도,위도 형식입니다.')
    const [longitude, latitude] = values.map(Number) as [number, number]
    if (
      !Number.isFinite(longitude) ||
      !Number.isFinite(latitude) ||
      Math.abs(longitude) > 180 ||
      Math.abs(latitude) > 90
    )
      fail('교차금지선 좌표가 유효하지 않습니다.')
    return { longitude, latitude }
  })
  if (points.length < 2) fail('교차금지선에는 두 개 이상의 좌표가 필요합니다.')
  return points
}
function intersects(a: Point, b: Point, c: Point, d: Point) {
  const cross = (p: Point, q: Point, r: Point) =>
    (q.longitude - p.longitude) * (r.latitude - p.latitude) -
    (q.latitude - p.latitude) * (r.longitude - p.longitude)
  const on = (p: Point, q: Point, r: Point) =>
    r.longitude >= Math.min(p.longitude, q.longitude) &&
    r.longitude <= Math.max(p.longitude, q.longitude) &&
    r.latitude >= Math.min(p.latitude, q.latitude) &&
    r.latitude <= Math.max(p.latitude, q.latitude)
  const x = cross(a, b, c),
    y = cross(a, b, d),
    z = cross(c, d, a),
    w = cross(c, d, b)
  return (
    (x * y < 0 && z * w < 0) ||
    (x === 0 && on(a, b, c)) ||
    (y === 0 && on(a, b, d)) ||
    (z === 0 && on(c, d, a)) ||
    (w === 0 && on(c, d, b))
  )
}
const formatTime = (ms: number) => {
  const d = new Date(ms),
    pad = (v: number) => String(v).padStart(2, '0')
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}`
}
export function planAllocation(state: TmsState, params: TmsPayload, now: number): DispatchResult {
  if (!['1', '2'].includes(text(params, 'allocationType'))) fail('allocationType은 1 또는 2입니다.')
  if (!/^([01]\d|2[0-3])[0-5]\d$/.test(text(params, 'startTime')))
    fail('startTime은 HHmm 형식의 유효한 시간이어야 합니다.')
  for (const key of ['optionType', 'equalizationType'])
    if (params[key] && !['1', '2', '3'].includes(text(params, key)))
      fail(`${key} 값은 1, 2, 3 중 하나입니다.`)
  if (params.centerReturnYn && !['Y', 'N'].includes(text(params, 'centerReturnYn')))
    fail('centerReturnYn은 Y 또는 N입니다.')
  if (!state.centers.length) fail('배차를 시작할 센터가 없습니다.')
  const pick = (list: TmsRow[], key: string, value: unknown) => {
    if (params.allocationType === '1') return list
    if (typeof value !== 'string' || !value.trim())
      fail('선택 배차에는 차량과 배송지 ID 목록이 필요합니다.')
    const ids = [
      ...new Set(
        String(value)
          .split(',')
          .map((s) => s.trim()),
      ),
    ]
    if (ids.some((id) => !list.some((r) => r[key] === id)))
      fail('선택 목록에 등록되지 않은 ID가 있습니다.', '404')
    return list.filter((r) => ids.includes(String(r[key])))
  }
  const vehicles = pick(state.vehicles, 'vehicleId', params.vehicleIdList).filter(
    (r) => r.inputYn !== '0',
  )
  const orders = pick(state.orders, 'orderId', params.orderIdList)
  if (!vehicles.length) fail('투입 가능한 차량이 없습니다.')
  if (!orders.length) fail('배차할 배송지가 없습니다.')
  const center = state.centers[0]!,
    origin = point(center)
  const lines = state.banLines.map((r) => parseLine(text(r, 'lineData')))
  const blocked = (a: Point, b: Point) =>
    lines.some((line) => line.slice(1).some((p, i) => intersects(a, b, line[i]!, p)))
  const start = new Date(now)
  start.setHours(
    Number(text(params, 'startTime').slice(0, 2)),
    Number(text(params, 'startTime').slice(2)),
    0,
    0,
  )
  const planned = vehicles.map((v) => ({
    vehicle: v,
    orders: [] as TmsRow[],
    weight: 0,
    volume: 0,
    distance: 0,
    seconds: 0,
    location: origin,
  }))
  const unassigned: DispatchResult['mock']['unassigned'] = []
  const endPoint = (v: TmsRow, last: Point) =>
    n(v, 'endLatitude') && n(v, 'endLongitude')
      ? { latitude: n(v, 'endLatitude'), longitude: n(v, 'endLongitude') }
      : params.centerReturnYn === 'N'
        ? last
        : origin
  for (const order of [...orders].sort(
    (a, b) => distanceMeters(origin, point(a)) - distanceMeters(origin, point(b)),
  )) {
    const typed = planned.filter((p) => p.vehicle.vehicleType === order.vehicleType)
    const zoned = typed.filter(
      (p) => !order.zoneCode || !p.vehicle.zoneCode || p.vehicle.zoneCode === order.zoneCode,
    )
    const capacity = zoned.filter(
      (p) =>
        p.weight + n(order, 'deliveryWeight') <= n(p.vehicle, 'weight') * 1000 + 1e-8 &&
        (n(p.vehicle, 'volume') === 0 ||
          p.volume + n(order, 'deliveryVolume') <= n(p.vehicle, 'volume') + 1e-8),
    )
    const allowed = capacity.filter(
      (p) =>
        !blocked(p.location, point(order)) &&
        !blocked(point(order), endPoint(p.vehicle, point(order))),
    )
    if (!allowed.length) {
      unassigned.push({
        orderId: text(order, 'orderId'),
        orderName: text(order, 'orderName'),
        reason: !typed.length
          ? '동일한 차량 유형이 없습니다.'
          : !zoned.length
            ? '동일 권역의 투입 차량이 없습니다.'
            : !capacity.length
              ? '중량 또는 부피 적재 한도를 초과합니다.'
              : '직선 경로가 교차금지선과 만납니다.',
      })
      continue
    }
    const score = (p: (typeof planned)[number]) => {
      const skill = n(p.vehicle, 'skillPer') / 100 || 1
      if (params.equalizationType === '2')
        return (p.distance + distanceMeters(p.location, point(order))) / skill
      if (params.equalizationType === '3')
        return (
          (p.seconds +
            distanceMeters(p.location, point(order)) / (30000 / 3600) +
            n(order, 'serviceTime') * 60) /
          skill
        )
      if (params.optionType === '3') return p.orders.length / skill
      if (params.optionType === '2') return p.volume / (n(p.vehicle, 'volume') || 1) / skill
      return p.weight / (n(p.vehicle, 'weight') * 1000) / skill
    }
    allowed.sort(
      (a, b) =>
        score(a) - score(b) ||
        distanceMeters(a.location, point(order)) - distanceMeters(b.location, point(order)),
    )
    const chosen = allowed[0]!,
      length = distanceMeters(chosen.location, point(order))
    chosen.orders.push(order)
    chosen.weight += n(order, 'deliveryWeight')
    chosen.volume += n(order, 'deliveryVolume')
    chosen.distance += length
    chosen.seconds += Math.ceil(length / (30000 / 3600)) + n(order, 'serviceTime') * 60
    chosen.location = point(order)
  }
  const vehicleList: VehiclePlan[] = planned
    .filter((p) => p.orders.length)
    .map((p) => {
      let at = start.getTime(),
        last = origin
      const orderList = p.orders.map((order) => {
        at += Math.ceil(distanceMeters(last, point(order)) / (30000 / 3600)) * 1000
        const arrival = formatTime(at)
        at += n(order, 'serviceTime') * 60000
        last = point(order)
        return {
          ...order,
          orderId: text(order, 'orderId'),
          latitude: String(order.latitude),
          longitude: String(order.longitude),
          expectedArrivalTime: arrival,
          expectedDepartureTime: formatTime(at),
        }
      })
      const end = endPoint(p.vehicle, last),
        returnDistance = distanceMeters(last, end)
      const location = (p: Point, address: string) => ({
        address,
        latitude: String(p.latitude),
        longitude: String(p.longitude),
      })
      const points = [origin, ...p.orders.map(point), ...(distanceMeters(last, end) ? [end] : [])]
      return {
        vehicleId: text(p.vehicle, 'vehicleId'),
        vehicleName: text(p.vehicle, 'vehicleName'),
        deliveryCount: p.orders.length,
        deliveryTime:
          Math.ceil((at - start.getTime()) / 1000) + Math.ceil(returnDistance / (30000 / 3600)),
        deliveryDistance: p.distance + returnDistance,
        deliveryWeight: p.weight,
        deliveryVolume: Number(p.volume.toFixed(4)),
        orderList,
        startLocation: location(origin, text(center, 'address')),
        endLocation: location(
          end,
          end === origin
            ? text(center, 'address')
            : text(p.vehicle, 'endAddress') || text(p.orders.at(-1)!, 'address'),
        ),
        routeList: [{ route: points.map((p) => `${p.longitude},${p.latitude}`).join('|') }],
      }
    })
  return {
    resultCode: '200',
    resultMessage: 'success',
    vehicleCount: String(vehicleList.length),
    vehicleList,
    mock: {
      simulated: true,
      routing: '직선 거리·가정 속도 기반 시연. 실제 도로 경로 및 TMS 최적화 결과가 아닙니다.',
      unassigned,
      assumptions: [
        '첫 번째 등록 센터에서 출발',
        '직선 거리와 시속 30km로 시간 추정',
        '중량 ton→kg 환산, 부피 0은 제한 미설정으로 처리',
        '숙련도는 배차 우선순위에 반영하는 목업 규칙',
        '교차금지선은 직선 구간 교차 여부로 검사',
      ],
    },
  }
}

export function executeTms(
  state: TmsState,
  path: string,
  raw: TmsPayload = {},
  now = Date.now(),
): TmsPayload {
  const operation = apiCatalog.find((o) => o.path === path)
  if (!operation) return fail('지원하지 않는 API입니다.', '404')
  if (!raw || typeof raw !== 'object' || Array.isArray(raw))
    return fail('요청은 JSON 객체여야 합니다.')
  const input = normalizedPayload(raw)
  validateParameters(operation, input)
  if (path === '/allocation') {
    const result = planAllocation(state, input, now)
    const mappingKey = `mock-${now}-${state.nextSeq++}`
    state.jobs[mappingKey] = { readyAt: now + 1200, result: clone(result) }
    const keys = Object.keys(state.jobs)
    if (keys.length > 30) delete state.jobs[keys[0]!]
    return { resultCode: '200', resultMessage: 'success', mappingKey }
  }
  if (path === '/allocationData') {
    if (input.routeYn && !['Y', 'N'].includes(text(input, 'routeYn')))
      fail('routeYn은 Y 또는 N입니다.')
    const job = state.jobs[text(input, 'mappingKey')]
    if (!job) return fail('mappingKey에 해당하는 배차 요청이 없습니다.', '404')
    if (now < job.readyAt)
      return {
        resultCode: '102',
        resultMessage: '목업 배차 처리 중',
        mappingKey: input.mappingKey,
        mockPending: true,
      }
    const result = clone(job.result)
    if (input.routeYn === 'Y') result.vehicleRouteList = clone(result.vehicleList)
    // Route-only properties belong to vehicleRouteList, matching the documented separation.
    const vehicleList = result.vehicleList.map((v) => {
      const row: TmsPayload = { ...v }
      delete row.startLocation
      delete row.endLocation
      delete row.routeList
      return row
    })
    return { ...result, vehicleList }
  }
  const resource = (Object.keys(resources) as Resource[]).find((key) =>
    path.startsWith(`/${resources[key].prefix}`),
  )!
  if (path.endsWith('List')) return success(state[resource])
  if (path.endsWith('ListInsert')) {
    const batch = raw.reqDatas ?? (raw.RAW_BODY as TmsPayload | undefined)?.reqDatas
    if (!Array.isArray(batch) || !batch.length || batch.length > 100)
      return fail('reqDatas에는 1~100개의 항목 배열을 넣으세요.')
    const shadow = clone(state)
    for (const row of batch) executeTms(shadow, `/${resources[resource].prefix}Insert`, row, now)
    state[resource] = shadow[resource]
    state.nextSeq = shadow.nextSeq
    return success()
  }
  return mutate(state, operation, resource, input, now)
}
