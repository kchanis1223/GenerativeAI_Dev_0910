import { describe, expect, it, beforeEach } from 'vitest'
import { createTmsState } from '../../src/data/logistics'
import { apiCatalog, executeTms, planAllocation } from '../../src/services/tms-mock'
import { callTms, resetTms, sampleRequest, tmsState } from '../../src/stores/tms'
const now = new Date('2026-09-10T00:00:00Z').getTime()
const params = {
  allocationType: '1',
  startTime: '0900',
  optionType: '1',
  equalizationType: '1',
  centerReturnYn: 'Y',
}
beforeEach(resetTms)

describe('명세 기반 CRUD', () => {
  it('24개 문서와 성공 예제가 있으며 모든 API가 실행된다', () => {
    expect(apiCatalog).toHaveLength(24)
    for (const operation of apiCatalog) {
      const state = createTmsState()
      const request = sampleRequest(operation)
      if (operation.path === '/zoneDelete') request.code = 'unused-zone'
      if (operation.path === '/zoneDelete')
        executeTms(state, '/zoneInsert', { code: 'unused-zone', name: '삭제 예제' }, now)
      if (operation.path === '/allocationData')
        request.mappingKey = executeTms(state, '/allocation', params, now).mappingKey
      expect(operation.examples.length).toBeGreaterThan(0)
      expect(
        executeTms(state, operation.path, request, now + 2000).resultCode,
        operation.path,
      ).toBe('200')
    }
  })
  it('차량 등록→수정→조회→선택 삭제가 같은 데이터에 반영된다', () => {
    const state = createTmsState()
    executeTms(state, '/vehicleInsert', {
      vehicleId: 'test',
      vehicleName: '테스트 차량',
      weight: 2,
      zoneCode: '0001',
    })
    executeTms(state, '/vehicleUpdate', { vehicleId: 'test', inputYn: '0', zoneCode: '' })
    expect(state.vehicles.at(-1)).toMatchObject({
      vehicleId: 'test',
      inputYn: '0',
      zoneCode: '',
      weight: 2,
    })
    expect(executeTms(state, '/vehicleList').resultCount).toBe(7)
    executeTms(state, '/vehicleDelete', { vehicleId: 'test,vehicle01', deleteFlag: '2' })
    expect(state.vehicles).toHaveLength(5)
  })
  it('일괄 등록은 오류가 있으면 부분 저장하지 않는다', () => {
    const state = createTmsState(),
      before = JSON.stringify(state)
    expect(() =>
      executeTms(state, '/orderListInsert', {
        reqDatas: [
          {
            orderId: 'new',
            orderName: '신규',
            latitude: 37,
            longitude: 127,
            deliveryWeight: '100',
          },
          {
            orderId: 'broken',
            orderName: '오류',
            latitude: 200,
            longitude: 127,
            deliveryWeight: '100',
          },
        ],
      }),
    ).toThrow('위도')
    expect(JSON.stringify(state)).toBe(before)
  })
  it('중복 ID·사용 중 권역·잘못된 선택 삭제는 데이터를 보존한다', () => {
    const state = createTmsState(),
      before = JSON.stringify(state)
    expect(() =>
      executeTms(state, '/vehicleInsert', {
        vehicleId: 'vehicle01',
        vehicleName: '중복',
        weight: 1,
      }),
    ).toThrow('이미 존재')
    expect(() => executeTms(state, '/zoneDelete', { code: '0001' })).toThrow('사용하는 권역')
    expect(() => executeTms(state, '/orderDelete', { deleteFlag: '2' })).toThrow('삭제할 ID')
    expect(JSON.stringify(state)).toBe(before)
  })
  it('전체 삭제는 deleteFlag 1에서만 실행된다', () => {
    const state = createTmsState()
    expect(() => executeTms(state, '/vehicleDelete', { deleteFlag: '3' })).toThrow()
    executeTms(state, '/vehicleDelete', { deleteFlag: '1' })
    expect(state.vehicles).toHaveLength(0)
  })
  it('타입·좌표·숙련도·필수 필드 오류를 거부한다', () => {
    for (const patch of [
      { weight: -1 },
      { skillPer: 55 },
      { vehicleType: '03' },
      { endLatitude: 99 },
      { vehicleName: '' },
    ]) {
      const state = createTmsState()
      expect(() =>
        executeTms(state, '/vehicleInsert', {
          vehicleId: 'new',
          vehicleName: '신규',
          weight: 1,
          ...patch,
        }),
      ).toThrow()
      expect(state.vehicles).toHaveLength(6)
    }
    expect(() => executeTms(createTmsState(), '/banLineInsert', { lineData: '127,37' })).toThrow()
  })
})

describe('배차 규칙과 비동기 응답', () => {
  it('ton을 kg로 환산하고 냉장·권역·투입 여부를 지킨다', () => {
    const state = createTmsState()
    const result = planAllocation(state, params, now)
    const assigned = result.vehicleList.flatMap((v) => v.orderList.map((o) => o.orderId))
    expect(assigned).toHaveLength(7)
    expect(new Set(assigned).size).toBe(7)
    expect(result.mock.unassigned).toEqual([
      {
        orderId: 'order08',
        orderName: '인천 미배차 예제',
        reason: '동일 권역의 투입 차량이 없습니다.',
      },
    ])
    for (const plan of result.vehicleList) {
      const vehicle = state.vehicles.find((v) => v.vehicleId === plan.vehicleId)!
      expect(vehicle.inputYn).toBe('1')
      expect(plan.deliveryWeight).toBeLessThanOrEqual(Number(vehicle.weight) * 1000)
      expect(plan.deliveryVolume).toBeLessThanOrEqual(Number(vehicle.volume))
      for (const order of plan.orderList) {
        expect(order.vehicleType).toBe(vehicle.vehicleType)
        expect(order.zoneCode).toBe(vehicle.zoneCode)
        expect(order.expectedArrivalTime).toMatch(/^\d{12}$/)
        expect(order.expectedDepartureTime >= order.expectedArrivalTime).toBe(true)
      }
    }
    expect(result.vehicleList.find((v) => v.vehicleId === 'vehicle03')?.orderList[0]?.orderId).toBe(
      'order03',
    )
  })
  it('선택 배차에서 초과 중량·부피와 미등록 ID를 처리한다', () => {
    const state = createTmsState()
    const selection = {
      ...params,
      allocationType: '2',
      vehicleIdList: 'vehicle01',
      orderIdList: 'order01,order02,order04,order07',
    }
    const result = planAllocation(state, selection, now)
    expect(result.mock.unassigned.length).toBeGreaterThan(0)
    expect(result.vehicleList[0]!.deliveryWeight).toBeLessThanOrEqual(1000)
    state.vehicles[0]!.volume = 0.5
    expect(planAllocation(state, selection, now).vehicleList).toHaveLength(0)
    expect(() => planAllocation(state, { ...selection, vehicleIdList: 'missing' }, now)).toThrow(
      '등록되지 않은',
    )
  })
  it('교차금지선을 통과하는 직선 배송을 배차하지 않는다', () => {
    const state = createTmsState()
    state.banLines = [
      { seq: 1, lineData: '126.965,37.50_126.965,37.60', lineName: '마포 방향 차단' },
    ]
    const result = planAllocation(
      state,
      { ...params, allocationType: '2', vehicleIdList: 'vehicle01', orderIdList: 'order01' },
      now,
    )
    expect(result.vehicleList).toHaveLength(0)
    expect(result.mock.unassigned[0]!.reason).toContain('교차금지선')
  })
  it('mappingKey는 처리 중 이후 결과를 반환하고 요청 당시 데이터를 유지한다', () => {
    const state = createTmsState()
    const receipt = executeTms(state, '/allocation', params, now)
    expect(
      executeTms(state, '/allocationData', { mappingKey: receipt.mappingKey }, now).resultCode,
    ).toBe('102')
    state.orders = []
    const result = executeTms(
      state,
      '/allocationData',
      { mappingKey: receipt.mappingKey, routeYn: 'Y' },
      now + 1200,
    )
    expect(result.resultCode).toBe('200')
    expect(result.vehicleList).toEqual(
      expect.arrayContaining([expect.objectContaining({ deliveryCount: expect.any(Number) })]),
    )
    expect(result.vehicleRouteList).toBeDefined()
    expect((result.vehicleList as Record<string, unknown>[])[0]!.routeList).toBeUndefined()
    expect(
      executeTms(
        state,
        '/allocationData',
        { mappingKey: receipt.mappingKey, routeYn: 'N' },
        now + 1200,
      ).vehicleRouteList,
    ).toBeUndefined()
    expect(() => executeTms(state, '/allocationData', { mappingKey: 'missing' })).toThrow(
      'mappingKey',
    )
  })
  it('복귀 여부에 따라 거리와 도착 위치가 달라진다', () => {
    const state = createTmsState()
    const selected = {
      ...params,
      allocationType: '2',
      vehicleIdList: 'vehicle01',
      orderIdList: 'order01',
    }
    const yes = planAllocation(state, selected, now).vehicleList[0]!
    const no = planAllocation(state, { ...selected, centerReturnYn: 'N' }, now).vehicleList[0]!
    expect(yes.deliveryDistance).toBe(no.deliveryDistance! * 2)
    expect(yes.endLocation).toEqual(yes.startLocation)
    expect(no.endLocation.latitude).toBe(String(state.orders[0]!.latitude))
  })
  it('인증 실패·타임아웃 시 변경을 커밋하지 않는다', async () => {
    const before = JSON.stringify(tmsState)
    const request = { vehicleId: 'new', vehicleName: '차량', weight: 1 }
    expect((await callTms('/vehicleInsert', request, 'unauthorized')).resultCode).toBe('401')
    expect((await callTms('/vehicleInsert', request, 'timeout')).resultCode).toBe('TIMEOUT')
    expect(JSON.stringify(tmsState)).toBe(before)
    expect((await callTms('/vehicleList', {}, 'empty')).resultCount).toBe(0)
    expect(tmsState.vehicles).toHaveLength(6)
  })
})
