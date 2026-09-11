import { afterEach, describe, expect, it, vi } from 'vitest'
import { createDeliveryData } from '../../src/data/noryangjin'
import { createDispatchConsole } from '../../src/stores/dispatch-console'
import { planAllocation } from '../../src/services/tms-mock'
import type { TmsPayload } from '../../src/types/tms'

const params = { allocationType: '1', startTime: '0900', optionType: '1', centerReturnYn: 'Y' }
const now = new Date('2026-09-12T00:00:00Z').getTime()
const disposers: (() => void)[] = []
function setup(...args: Parameters<typeof createDispatchConsole>) {
  const store = createDispatchConsole(...args)
  disposers.push(store.dispose)
  return store
}
afterEach(() => {
  disposers.splice(0).forEach((fn) => fn())
  vi.useRealTimers()
})

describe('노량진 CSV 배차', () => {
  it('40개 주문을 적재 한도와 품목에 맞게 배정하고 배송 데이터 날짜를 사용한다', () => {
    const { state } = createDeliveryData()
    const result = planAllocation(state, params, now, {
      centerId: 'CENTER-NR',
      deliveryDate: '2026-09-11',
      returnToCenter: true,
    })
    expect(result.vehicleList).toHaveLength(5)
    expect(result.mock.unassigned).toEqual([])
    const assigned = result.vehicleList.flatMap((p) => p.orderList)
    expect(assigned).toHaveLength(40)
    expect(new Set(assigned.map((o) => o.orderId)).size).toBe(40)
    for (const plan of result.vehicleList) {
      const vehicle = state.vehicles.find((v) => v.vehicleId === plan.vehicleId)!
      expect(plan.deliveryWeight).toBeLessThanOrEqual(Number(vehicle.maxLoadKg))
      expect(plan.endLocation).toEqual(plan.startLocation)
      for (const order of plan.orderList) {
        expect(String(vehicle.supportedItemTypes).split('|')).toContain(order.itemType)
        expect(order.expectedArrivalTime.startsWith('20260911')).toBe(true)
      }
    }
  })
  it('냉장 전용 차량에 냉동 주문을 섞지 않으며 미배차 이유를 반환한다', () => {
    const { state } = createDeliveryData()
    const frozen = state.orders.filter((o) => o.itemType === '냉동')
    const result = planAllocation(
      state,
      {
        ...params,
        allocationType: '2',
        vehicleIdList: 'COLD01',
        orderIdList: frozen.map((o) => o.orderId).join(','),
      },
      now,
    )
    expect(result.vehicleList).toHaveLength(0)
    expect(result.mock.unassigned).toHaveLength(10)
    expect(result.mock.unassigned[0]?.reason).toContain('품목')
  })
  it('센터 복귀 설정을 해제하면 CSV 차량의 기본 종착지 대신 마지막 배송지에서 끝난다', () => {
    const { state } = createDeliveryData()
    const yes = planAllocation(state, params, now, { returnToCenter: true })
    const no = planAllocation(state, params, now, { returnToCenter: false })
    no.vehicleList.forEach((plan, index) => {
      const last = plan.orderList.at(-1)!
      expect(plan.endLocation).toEqual({
        address: last.address,
        latitude: String(last.latitude),
        longitude: String(last.longitude),
      })
      expect(plan.deliveryDistance).toBeLessThan(yes.vehicleList[index]!.deliveryDistance)
    })
  })
})

describe('단일 화면 배차 수명 주기', () => {
  it('주문이나 차량을 선택하지 않으면 요청하지 않는다', async () => {
    const client = vi.fn()
    const store = setup(undefined, client)
    store.state.orderIds = []
    await store.run()
    expect(store.state.error).toContain('주문')
    expect(client).not.toHaveBeenCalled()
    store.state.orderIds = store.data.orders.map((o) => String(o.orderId))
    store.state.vehicleIds = []
    await store.run()
    expect(store.state.error).toContain('차량')
    expect(client).not.toHaveBeenCalled()
  })
  it('모달을 닫아도 계산을 완료하고 중복 요청 대신 진행 창을 다시 연다', async () => {
    vi.useFakeTimers()
    const store = setup()
    const running = store.run()
    store.state.modalOpen = false
    await store.run()
    expect(store.state.modalOpen).toBe(true)
    store.state.modalOpen = false
    await vi.advanceTimersByTimeAsync(2500)
    await running
    expect(Object.keys(store.data.jobs)).toHaveLength(1)
    expect(store.state.busy).toBe(false)
    expect(store.state.result?.vehicleList).toHaveLength(5)
    expect(store.state.visibleVehicleIds).toHaveLength(5)
    expect(store.state.snapshot).toMatchObject({
      orders: 40,
      vehicles: 5,
      branches: 20,
      weight: 3125,
    })
    expect(store.state.modalOpen).toBe(false)
    expect(vi.getTimerCount()).toBe(0)
    store.state.centerReturn = false
    expect(store.state.result).toBeNull()
    expect(store.state.visibleVehicleIds).toEqual([])
    expect(store.state.notice).toContain('다시 요청')
  })
  it('취소 이후 늦은 응답이 도착해도 결과를 덮어쓰지 않는다', async () => {
    vi.useFakeTimers()
    let resolve!: (value: TmsPayload) => void
    const client = vi.fn(
      () =>
        new Promise<TmsPayload>((done) => {
          resolve = done
        }),
    )
    const store = setup(undefined, client)
    const running = store.run()
    store.cancel()
    resolve({ resultCode: '200', mappingKey: 'late-result' })
    await running
    expect(store.state.busy).toBe(false)
    expect(store.state.result).toBeNull()
    expect(store.state.mappingKey).toBe('')
    expect(client).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })
  it('요청 실패 후 선택을 유지하고 재시도로 복구한다', async () => {
    vi.useFakeTimers()
    const data = createDeliveryData().state
    const result = planAllocation(data, params, now)
    const client = vi
      .fn()
      .mockRejectedValueOnce(new Error('연결 실패'))
      .mockResolvedValueOnce({ resultCode: '200', mappingKey: 'retry' })
      .mockResolvedValueOnce(result)
    const store = setup(data, client)
    await store.run()
    expect(store.state.error).toBe('연결 실패')
    expect(store.state.vehicleIds).toHaveLength(5)
    expect(store.state.busy).toBe(false)
    const retry = store.run()
    await vi.advanceTimersByTimeAsync(1000)
    await retry
    expect(store.state.result?.vehicleCount).toBe('5')
    expect(store.state.error).toBe('')
  })
  it('계산 중 응답이 반복되면 정해진 횟수 후 중단한다', async () => {
    vi.useFakeTimers()
    const client = vi
      .fn()
      .mockResolvedValueOnce({ resultCode: '200', mappingKey: 'pending' })
      .mockResolvedValue({ resultCode: '102' })
    const store = setup(undefined, client)
    const running = store.run()
    await vi.advanceTimersByTimeAsync(6000)
    await running
    expect(client).toHaveBeenCalledTimes(13)
    expect(store.state.error).toContain('초과')
    expect(store.state.busy).toBe(false)
    expect(vi.getTimerCount()).toBe(0)
  })
})
