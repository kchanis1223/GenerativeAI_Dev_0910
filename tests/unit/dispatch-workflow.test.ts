import { afterEach, describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'
import { createTmsState } from '../../src/data/logistics'
import { createDispatchWorkflow } from '../../src/stores/dispatch-workflow'
import { executeTms, planAllocation } from '../../src/services/tms-mock'
import type { callTms } from '../../src/stores/tms'
import type { TmsPayload } from '../../src/types/tms'
const scopes: ReturnType<typeof createDispatchWorkflow>[] = []
afterEach(() => {
  scopes.splice(0).forEach((f) => f.dispose())
  vi.useRealTimers()
})
function setup(client?: typeof callTms) {
  const data = reactive(createTmsState())
  const now = Date.now()
  const request =
    client ??
    vi.fn<typeof callTms>(async (path, payload, _scenario, context) =>
      executeTms(data, path, payload, now + (path === '/allocationData' ? 2000 : 0), context),
    )
  const flow = createDispatchWorkflow(data, request)
  scopes.push(flow)
  return { data, flow, request }
}
function prepare(flow: ReturnType<typeof createDispatchWorkflow>, centerId = 'euljiro_center') {
  flow.state.centerId = centerId
  flow.next()
  flow.state.orderIds = ['order01']
  flow.next()
  flow.state.vehicleIds = ['vehicle01']
  flow.next()
  flow.next()
}
describe('배송 준비 흐름', () => {
  it('필수 선택과 단계 순서를 검증한다', () => {
    const { flow } = setup()
    flow.next()
    expect(flow.state.step).toBe(1)
    flow.go(5)
    expect(flow.state.step).toBe(1)
    flow.state.centerId = 'euljiro_center'
    flow.next()
    flow.next()
    expect(flow.state.step).toBe(2)
    flow.state.orderIds = ['order01']
    flow.next()
    flow.next()
    expect(flow.state.step).toBe(3)
    flow.state.vehicleIds = ['vehicle05']
    flow.next()
    expect(flow.state.step).toBe(3)
    flow.state.vehicleIds = ['vehicle01']
    flow.next()
    flow.state.startTime = '25:00'
    flow.next()
    expect(flow.state.step).toBe(4)
  })
  it('선택한 센터와 대상만 계산하며 중복 요청을 막고 결과에서 상세로 진행한다', async () => {
    vi.useFakeTimers()
    const { flow, data, request } = setup()
    const id = String(data.centers[1]!.centerId)
    prepare(flow, id)
    const pending = flow.run()
    await flow.run()
    expect(flow.state.step).toBe(6)
    await vi.runAllTimersAsync()
    await pending
    expect(flow.state.step).toBe(7)
    expect(vi.mocked(request).mock.calls.filter(([p]) => p === '/allocation')).toHaveLength(1)
    expect(vi.mocked(request).mock.calls[0]![1]).toMatchObject({
      allocationType: '2',
      orderIdList: 'order01',
      vehicleIdList: 'vehicle01',
    })
    expect(vi.mocked(request).mock.calls[0]![1]).not.toHaveProperty('centerId')
    expect(flow.state.result!.vehicleRouteList![0]!.startLocation.latitude).toBe(
      String(data.centers[1]!.latitude),
    )
    expect(flow.totalAssigned.value).toBe(1)
    flow.next()
    expect(flow.state.step).toBe(8)
    flow.go(1)
    flow.state.centerId = String(data.centers[2]!.centerId)
    expect(flow.state.result).toBeNull()
    expect(flow.canVisit(7)).toBe(false)
  })
  it('삭제되거나 운행 제외된 선택을 제거하고 진행을 막는다', () => {
    const { flow, data } = setup()
    prepare(flow)
    data.vehicles[0]!.inputYn = '0'
    expect(flow.state.vehicleIds).toEqual([])
    expect(flow.state.step).toBe(3)
    data.orders = []
    expect(flow.state.orderIds).toEqual([])
    expect(flow.state.step).toBe(2)
    data.centers = []
    expect(flow.state.centerId).toBe('')
    expect(flow.state.step).toBe(1)
  })
  it('실패 시 확인 단계로 돌아오고 선택을 유지해 재시도할 수 있다', async () => {
    const request = vi
      .fn<typeof callTms>()
      .mockResolvedValue({ resultCode: '401', resultMessage: '인증 오류' })
    const { flow } = setup(request)
    prepare(flow)
    await flow.run()
    expect(flow.state.step).toBe(5)
    expect(flow.state.busy).toBe(false)
    expect(flow.state.error).toBe('인증 오류')
    expect(flow.state.orderIds).toEqual(['order01'])
    await flow.run()
    expect(request).toHaveBeenCalledTimes(2)
  })
  it('계산 중 계속 반환되면 8회 뒤 종료한다', async () => {
    vi.useFakeTimers()
    const request = vi.fn<typeof callTms>(async (path) =>
      path === '/allocation' ? { resultCode: '200', mappingKey: 'test' } : { resultCode: '102' },
    )
    const { flow } = setup(request)
    prepare(flow)
    const promise = flow.run()
    await vi.runAllTimersAsync()
    await promise
    expect(request).toHaveBeenCalledTimes(9)
    expect(flow.state.step).toBe(5)
    expect(flow.state.error).toContain('제시간')
    expect(flow.state.busy).toBe(false)
  })
  it('계산 중 선택 정보가 바뀌면 늦게 도착한 응답을 표시하지 않는다', async () => {
    let resolve!: (v: TmsPayload) => void
    const request = vi.fn<typeof callTms>(
      () =>
        new Promise((r) => {
          resolve = r
        }),
    )
    const { flow } = setup(request)
    prepare(flow)
    const pending = flow.run()
    flow.state.orderIds = []
    resolve({ resultCode: '200', mappingKey: 'old-result' })
    await pending
    expect(flow.state.result).toBeNull()
    expect(flow.state.mappingKey).toBe('')
    expect(flow.state.step).toBe(2)
    expect(flow.state.busy).toBe(false)
    expect(request).toHaveBeenCalledTimes(1)
  })
  it('존재하지 않는 센터로 배차하지 않고 센터 순서를 변경하지 않는다', () => {
    const data = createTmsState(),
      ids = data.centers.map((c) => c.centerId)
    const params = {
      allocationType: '2',
      orderIdList: 'order01',
      vehicleIdList: 'vehicle01',
      startTime: '0900',
    }
    expect(() => planAllocation(data, params, Date.now(), { centerId: 'missing' })).toThrow(
      '선택한 센터',
    )
    planAllocation(data, params, Date.now(), { centerId: String(data.centers[1]!.centerId) })
    expect(data.centers.map((c) => c.centerId)).toEqual(ids)
  })
})
