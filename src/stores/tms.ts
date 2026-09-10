import { reactive } from 'vue'
import { createTmsState, resources } from '../data/logistics'
import { apiCatalog, executeTms, TmsError } from '../services/tms-mock'
import type { ApiOperation, TmsLog, TmsPayload } from '../types/tms'

export const tmsState = reactive(createTmsState())
export const tmsLogs = reactive<TmsLog[]>([])
export type MockScenario = 'success' | 'unauthorized' | 'timeout' | 'empty'
const copy = <T>(v: T): T => JSON.parse(JSON.stringify(v))
export function resetTms() {
  Object.assign(tmsState, createTmsState())
  tmsLogs.splice(0)
}
export async function callTms(
  path: string,
  input: TmsPayload = {},
  scenario: MockScenario = 'success',
): Promise<TmsPayload> {
  const started = Date.now()
  const request = copy(input)
  delete request.appKey
  let response: TmsPayload
  await new Promise((resolve) => setTimeout(resolve, scenario === 'timeout' ? 1000 : 250))
  try {
    if (scenario === 'unauthorized') throw new TmsError('401', '목업 인증 오류입니다.')
    if (scenario === 'timeout') throw new TmsError('TIMEOUT', '목업 요청 시간이 초과되었습니다.')
    if (scenario === 'empty' && !path.endsWith('List'))
      throw new TmsError('400', '빈 목록 시나리오는 목록 조회에서만 사용할 수 있습니다.')
    response =
      scenario === 'empty'
        ? { resultCode: '200', resultCount: 0, resultMessage: 'success', resultData: [] }
        : executeTms(tmsState, path, request)
  } catch (error) {
    response = {
      resultCode: error instanceof TmsError ? error.code : '400',
      resultMessage: error instanceof Error ? error.message : '요청을 처리하지 못했습니다.',
    }
  }
  const operation = apiCatalog.find((o) => o.path === path)!
  tmsLogs.unshift({
    id: crypto.randomUUID(),
    time: new Date().toLocaleTimeString('ko-KR'),
    path,
    title: operation.title,
    method: operation.method,
    request,
    response: copy(response),
    status:
      response.resultCode === '200'
        ? 'success'
        : response.resultCode === '102'
          ? 'pending'
          : 'error',
    duration: Date.now() - started,
  })
  if (tmsLogs.length > 50) tmsLogs.splice(50)
  return response
}
export function sampleRequest(operation: ApiOperation): TmsPayload {
  const suffix = tmsState.nextSeq
  const resource = Object.entries(resources).find(([, m]) =>
    operation.path.startsWith(`/${m.prefix}`),
  )
  const row = resource ? tmsState[resource[0] as keyof typeof resources][0] : undefined
  const values: TmsPayload = {
    centerId: `center${suffix}`,
    centerName: '새 물류센터',
    address: '서울특별시 중구 을지로 65',
    latitude: 37.566482,
    longitude: 126.985085,
    code: `zone${suffix}`,
    name: '신규 권역',
    vehicleId: `vehicle${suffix}`,
    vehicleName: '신규 배송 차량',
    weight: 1,
    volume: 8,
    vehicleType: '01',
    zoneCode: String(tmsState.zones[0]?.code ?? ''),
    inputYn: '1',
    skillPer: 100,
    endLatitude: 0,
    endLongitude: 0,
    orderId: `order${suffix}`,
    orderName: '신규 배송지',
    deliveryWeight: '250',
    deliveryVolume: '1',
    serviceTime: 10,
    deleteFlag: '2',
    allocationType: '1',
    startTime: '0900',
    optionType: '1',
    equalizationType: '1',
    centerReturnYn: 'Y',
    routeYn: 'Y',
    mappingKey: Object.keys(tmsState.jobs).at(-1) ?? '배차 요청 후 받은 mappingKey',
    lineName: '새 통제구간',
    lineData: '127.20,37.70_127.20,37.75',
    seq: row?.seq ?? 124,
  }
  if (operation.path.endsWith('ListInsert')) {
    const single = apiCatalog.find(
      (o) => o.path === operation.path.replace('ListInsert', 'Insert'),
    )!
    const first = sampleRequest(single)
    const id = resource![1].id
    return { reqDatas: [first, { ...first, [id]: `${first[id]}_2` }] }
  }
  const result: TmsPayload = {}
  for (const p of operation.parameters) {
    const isExisting = operation.path.endsWith('Update') || operation.path.endsWith('Delete')
    const value = isExisting && row?.[p.name] !== undefined ? row[p.name] : values[p.name]
    if (value !== undefined) result[p.name] = value
  }
  return result
}
