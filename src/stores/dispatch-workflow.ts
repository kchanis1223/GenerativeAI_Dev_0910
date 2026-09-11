import { computed, effectScope, reactive, watch } from 'vue'
import { callTms, tmsState } from './tms'
import type { DispatchResult, TmsPayload, TmsState } from '../types/tms'

export const dispatchSteps = [
  '센터 선택',
  '오늘 배송할 주문 등록/선택',
  '운행 가능한 차량 선택',
  '배차 조건 설정',
  '배차 요청',
  '계산 중',
  '배차 결과 확인',
  '차량별 배송 순서 / 예상시간 / 경로 확인',
]
export function createDispatchWorkflow(
  data: TmsState = tmsState,
  request: typeof callTms = callTms,
) {
  const state = reactive({
    step: 1,
    furthest: 1,
    centerId: '',
    orderIds: [] as string[],
    vehicleIds: [] as string[],
    startTime: '09:00',
    optionType: '1',
    equalizationType: '1',
    centerReturnYn: 'Y',
    routeYn: 'Y',
    busy: false,
    mappingKey: '',
    error: '',
    notice: '',
    result: null as DispatchResult | null,
    snapshot: null as {
      centerId: string
      centerName: string
      request: TmsPayload
      routeYn: string
    } | null,
  })
  const center = computed(() => data.centers.find((c) => c.centerId === state.centerId))
  const orders = computed(() =>
    data.orders.filter((o) => state.orderIds.includes(String(o.orderId))),
  )
  const availableVehicles = computed(() => data.vehicles.filter((v) => v.inputYn !== '0'))
  const vehicles = computed(() =>
    availableVehicles.value.filter((v) => state.vehicleIds.includes(String(v.vehicleId))),
  )
  const weight = computed(() => orders.value.reduce((sum, o) => sum + Number(o.deliveryWeight), 0))
  const totalAssigned = computed(
    () => state.result?.vehicleList.reduce((sum, v) => sum + v.deliveryCount, 0) ?? 0,
  )
  function issue(step: number) {
    if (!center.value) return '출발할 센터를 선택해 주세요.'
    if (step >= 2 && (!orders.value.length || orders.value.length !== state.orderIds.length))
      return '오늘 배송할 주문을 1건 이상 선택해 주세요.'
    if (step >= 3 && (!vehicles.value.length || vehicles.value.length !== state.vehicleIds.length))
      return '운행 가능한 차량을 1대 이상 선택해 주세요.'
    if (
      step >= 4 &&
      (!/^([01]\d|2[0-3]):[0-5]\d$/.test(state.startTime) ||
        !['1', '2', '3'].includes(state.optionType) ||
        !['1', '2', '3'].includes(state.equalizationType) ||
        !['Y', 'N'].includes(state.centerReturnYn) ||
        !['Y', 'N'].includes(state.routeYn))
    )
      return '배차 조건과 출발 시간을 확인해 주세요.'
    return ''
  }
  function canVisit(step: number) {
    return (
      !state.busy &&
      step >= 1 &&
      step <= state.furthest &&
      step !== 6 &&
      (step === 1 || !issue(Math.min(step - 1, 4))) &&
      (step < 7 || !!state.result)
    )
  }
  function go(step: number) {
    if (canVisit(step)) {
      state.step = step
      state.error = ''
    }
  }
  function next() {
    if (state.busy) return
    const message = issue(Math.min(state.step, 4))
    if (message) {
      state.error = message
      return
    }
    if (state.step < 5 || (state.step === 7 && state.result)) {
      state.step++
      state.furthest = Math.max(state.furthest, state.step)
      state.error = ''
    }
  }
  let version = 0
  const scope = effectScope()
  scope.run(() => {
    watch(
      () =>
        JSON.stringify([
          data.centers.map((c) => c.centerId),
          data.orders.map((o) => o.orderId),
          availableVehicles.value.map((v) => v.vehicleId),
        ]),
      () => {
        if (!center.value) state.centerId = ''
        state.orderIds = state.orderIds.filter((id) => data.orders.some((o) => o.orderId === id))
        state.vehicleIds = state.vehicleIds.filter((id) =>
          availableVehicles.value.some((v) => v.vehicleId === id),
        )
      },
      { flush: 'sync' },
    )
    watch(
      () =>
        JSON.stringify([
          state.centerId,
          state.orderIds,
          state.vehicleIds,
          center.value,
          orders.value,
          vehicles.value,
          data.banLines,
          data.zones,
          state.startTime,
          state.optionType,
          state.equalizationType,
          state.centerReturnYn,
          state.routeYn,
        ]),
      () => {
        version++
        if (state.result || state.busy)
          state.notice =
            '선택 정보가 변경되어 이전 결과를 초기화했습니다. 배차를 다시 요청해 주세요.'
        state.result = null
        state.snapshot = null
        state.mappingKey = ''
        state.busy = false
        state.error = ''
        const limit = !center.value
          ? 1
          : !orders.value.length
            ? 2
            : !vehicles.value.length
              ? 3
              : issue(4)
                ? 4
                : 5
        state.furthest = Math.min(state.furthest, limit)
        if (state.step > state.furthest) state.step = state.furthest
      },
      { flush: 'sync' },
    )
  })
  async function run() {
    if (state.busy || state.step !== 5) return
    const message = issue(4)
    if (message) {
      state.error = message
      return
    }
    const payload: TmsPayload = {
      allocationType: '2',
      orderIdList: state.orderIds.join(','),
      vehicleIdList: state.vehicleIds.join(','),
      startTime: state.startTime.replace(':', ''),
      optionType: state.optionType,
      equalizationType: state.equalizationType,
      centerReturnYn: state.centerReturnYn,
    }
    const snapshot = {
      centerId: state.centerId,
      centerName: String(center.value!.centerName),
      request: payload,
      routeYn: state.routeYn,
    }
    state.snapshot = snapshot
    state.error = ''
    state.notice = ''
    state.result = null
    state.mappingKey = ''
    state.busy = true
    state.step = 6
    const current = ++version
    try {
      const receipt = await request('/allocation', payload, 'success', {
        centerId: snapshot.centerId,
      })
      if (current !== version) return
      if (receipt.resultCode !== '200') throw new Error(String(receipt.resultMessage))
      state.mappingKey = String(receipt.mappingKey)
      for (let attempt = 0; attempt < 8; attempt++) {
        await new Promise((resolve) => setTimeout(resolve, 400))
        if (current !== version) return
        const response = await request('/allocationData', {
          mappingKey: state.mappingKey,
          routeYn: snapshot.routeYn,
        })
        if (current !== version) return
        if (response.resultCode === '102') continue
        if (response.resultCode !== '200') throw new Error(String(response.resultMessage))
        state.result = response as unknown as DispatchResult
        state.step = 7
        state.furthest = 7
        return
      }
      throw new Error('계산 결과를 제시간에 받지 못했습니다. 다시 요청해 주세요.')
    } catch (error) {
      if (current !== version) return
      state.error = error instanceof Error ? error.message : '배차 요청에 실패했습니다.'
      state.step = 5
    } finally {
      if (current === version) state.busy = false
    }
  }
  function restart() {
    if (state.busy) return
    version++
    Object.assign(state, {
      step: 1,
      furthest: 1,
      centerId: '',
      orderIds: [],
      vehicleIds: [],
      result: null,
      snapshot: null,
      mappingKey: '',
      error: '',
      notice: '',
    })
  }
  return {
    state,
    center,
    orders,
    vehicles,
    availableVehicles,
    weight,
    totalAssigned,
    issue,
    canVisit,
    go,
    next,
    run,
    restart,
    dispose: () => {
      version++
      scope.stop()
    },
  }
}
export const dispatchWorkflow = createDispatchWorkflow()
