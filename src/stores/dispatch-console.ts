import { computed, effectScope, reactive, watch } from 'vue'
import { createDeliveryData } from '../data/noryangjin'
import { agentDisplay } from '../services/agent-display'
import type { AgentReply } from '../services/agent'
import { executeTms } from '../services/tms-mock'
import type { DispatchResult, MockContext, TmsPayload, TmsState } from '../types/tms'

export type DispatchRequest = (
  path: string,
  payload: TmsPayload,
  context?: MockContext,
) => Promise<TmsPayload>
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function createDispatchConsole(
  data: TmsState = createDeliveryData().state,
  client?: DispatchRequest,
) {
  const request: DispatchRequest =
    client ??
    (async (path, payload, context) => {
      await wait(250)
      return executeTms(data, path, payload, Date.now(), context)
    })
  const state = reactive({
    agentBusy: false,
    agentSource: '',
    centerId: String(data.centers[0]?.centerId ?? ''),
    deliveryDate: String(data.orders[0]?.deliveryDate ?? ''),
    orderIds: data.orders.map((o) => String(o.orderId)),
    vehicleIds: data.vehicles.filter((v) => v.inputYn !== '0').map((v) => String(v.vehicleId)),
    startTime: '09:00',
    optionType: '1',
    centerReturn: true,
    busy: false,
    modalOpen: false,
    elapsed: 0,
    phase: 'request' as 'request' | 'calculating',
    error: '',
    notice: '',
    mappingKey: '',
    result: null as DispatchResult | null,
    snapshot: null as {
      centerName: string
      vehicles: number
      orders: number
      branches: number
      weight: number
      returnToCenter: boolean
    } | null,
    activeVehicleId: '',
    visibleVehicleIds: [] as string[],
    resultsOpen: true,
  })
  const center = computed(() => data.centers.find((c) => c.centerId === state.centerId))
  const availableOrders = computed(() =>
    data.orders.filter(
      (o) => o.centerId === state.centerId && o.deliveryDate === state.deliveryDate,
    ),
  )
  const availableVehicles = computed(() =>
    data.vehicles.filter((v) => v.centerId === state.centerId && v.inputYn !== '0'),
  )
  const orders = computed(() =>
    availableOrders.value.filter((o) => state.orderIds.includes(String(o.orderId))),
  )
  const vehicles = computed(() =>
    availableVehicles.value.filter((v) => state.vehicleIds.includes(String(v.vehicleId))),
  )
  const branchCount = computed(() => new Set(orders.value.map((o) => o.branchId)).size)
  const weight = computed(() => orders.value.reduce((sum, o) => sum + Number(o.deliveryWeight), 0))
  const plans = computed(() => state.result?.vehicleRouteList ?? state.result?.vehicleList ?? [])
  const activePlan = computed(() => plans.value.find((p) => p.vehicleId === state.activeVehicleId))
  const issue = computed(() =>
    !center.value
      ? '출발할 센터를 선택해 주세요.'
      : !orders.value.length
        ? '배송할 주문을 1건 이상 선택해 주세요.'
        : !vehicles.value.length
          ? '운행할 차량을 1대 이상 선택해 주세요.'
          : !/^([01]\d|2[0-3]):[0-5]\d$/.test(state.startTime)
            ? '출발 시간을 확인해 주세요.'
            : !['1', '2', '3'].includes(state.optionType)
              ? '배차 기준을 확인해 주세요.'
              : '',
  )
  let version = 0
  let ticker: ReturnType<typeof setInterval> | undefined
  const clearTicker = () => {
    clearInterval(ticker)
    ticker = undefined
  }
  const scope = effectScope()
  scope.run(() =>
    watch(
      () =>
        JSON.stringify([
          state.centerId,
          state.deliveryDate,
          state.orderIds,
          state.vehicleIds,
          state.startTime,
          state.optionType,
          state.centerReturn,
        ]),
      () => {
        version++
        clearTicker()
        if (state.result || state.busy)
          state.notice = '선택 조건이 바뀌었습니다. 배차를 다시 요청해 주세요.'
        state.busy = false
        state.modalOpen = false
        state.result = null
        state.snapshot = null
        state.mappingKey = ''
        state.activeVehicleId = ''
        state.visibleVehicleIds = []
        state.error = ''
        state.agentSource = ''
      },
      { flush: 'sync' },
    ),
  )

  function clearAgent() {
    version++
    clearTicker()
    state.result = null
    state.activeVehicleId = ''
    state.visibleVehicleIds = []
    state.notice = ''
    state.error = ''
    state.agentSource = ''
    state.orderIds = []
    state.vehicleIds = []
    state.snapshot = null
    state.busy = false
    state.modalOpen = false
  }
  function applyAgentReply(reply: AgentReply) {
    clearAgent()
    const p = reply.presentation
    if (!p) return
    if (reply.request) {
      state.centerId = reply.request.depot_id
      state.deliveryDate = reply.request.delivery_date
      state.startTime = reply.request.departure_time?.slice(11, 16) ?? '06:00'
    }
    state.orderIds = p.orders.map((o) => o.order_id)
    state.vehicleIds = p.vehicle_ids
    state.agentSource = p.source + ' · 확정 좌표 간 직선 경로 · ETA·거리 미제공'
    try {
      state.result = agentDisplay(reply, data)
      state.visibleVehicleIds = state.result?.vehicleList.map((v) => v.vehicleId) ?? []
      state.activeVehicleId = state.visibleVehicleIds[0] ?? ''
      state.notice = reply.message
      if (reply.status === 'error' || reply.status === 'blocked') state.error = reply.message
      state.resultsOpen = true
    } catch (error) {
      state.error = error instanceof Error ? error.message : '결과 표시 실패'
    }
  }
  async function run() {
    if (state.agentBusy) return
    state.agentSource = ''
    if (state.busy) {
      state.modalOpen = true
      return
    }
    if (issue.value) {
      state.error = issue.value
      return
    }
    const payload: TmsPayload = {
      allocationType: '2',
      orderIdList: orders.value.map((o) => o.orderId).join(','),
      vehicleIdList: vehicles.value.map((v) => v.vehicleId).join(','),
      startTime: state.startTime.replace(':', ''),
      optionType: state.optionType,
      equalizationType: '1',
      centerReturnYn: state.centerReturn ? 'Y' : 'N',
    }
    const context: MockContext = {
      centerId: state.centerId,
      deliveryDate: state.deliveryDate,
      returnToCenter: state.centerReturn,
    }
    state.snapshot = {
      centerName: String(center.value!.centerName),
      vehicles: vehicles.value.length,
      orders: orders.value.length,
      branches: branchCount.value,
      weight: weight.value,
      returnToCenter: state.centerReturn,
    }
    state.result = null
    state.error = ''
    state.notice = ''
    state.mappingKey = ''
    state.busy = true
    state.modalOpen = true
    state.elapsed = 0
    state.phase = 'request'
    const current = ++version
    const startedAt = Date.now()
    clearTicker()
    ticker = setInterval(() => {
      state.elapsed = Math.floor((Date.now() - startedAt) / 1000)
    }, 250)
    try {
      const receipt = await request('/allocation', payload, context)
      if (current !== version) return
      if (receipt.resultCode !== '200' || !receipt.mappingKey)
        throw new Error(String(receipt.resultMessage ?? '배차 요청에 실패했습니다.'))
      state.mappingKey = String(receipt.mappingKey)
      state.phase = 'calculating'
      for (let attempt = 0; attempt < 12; attempt++) {
        await wait(400)
        if (current !== version) return
        const response = await request('/allocationData', {
          mappingKey: state.mappingKey,
          routeYn: 'Y',
        })
        if (current !== version) return
        if (response.resultCode === '102') continue
        if (response.resultCode !== '200')
          throw new Error(String(response.resultMessage ?? '결과를 불러오지 못했습니다.'))
        const result = response as unknown as DispatchResult
        if (!Array.isArray(result.vehicleList) || !result.mock)
          throw new Error('배차 결과 형식을 확인해 주세요.')
        state.result = result
        state.activeVehicleId = result.vehicleList[0]?.vehicleId ?? ''
        state.visibleVehicleIds = result.vehicleList.map((v) => v.vehicleId)
        state.resultsOpen = true
        state.modalOpen = false
        state.notice = `배차 완료 · ${result.vehicleList.length}대 · ${result.vehicleList.reduce((sum, v) => sum + v.deliveryCount, 0)}건 배정${result.mock.unassigned.length ? ` · 미배차 ${result.mock.unassigned.length}건` : ''}`
        return
      }
      throw new Error('계산 시간이 초과되었습니다. 다시 요청해 주세요.')
    } catch (error) {
      if (current === version)
        state.error = error instanceof Error ? error.message : '배차 요청에 실패했습니다.'
    } finally {
      if (current === version) {
        state.busy = false
        clearTicker()
      }
    }
  }
  function cancel() {
    version++
    clearTicker()
    state.busy = false
    state.modalOpen = false
    state.mappingKey = ''
    state.notice = '배차를 취소했습니다. 조건을 확인하고 다시 요청할 수 있습니다.'
  }
  return {
    data,
    state,
    center,
    availableOrders,
    availableVehicles,
    orders,
    vehicles,
    branchCount,
    weight,
    plans,
    activePlan,
    issue,
    run,
    applyAgentReply,
    clearAgent,
    cancel,
    dispose: () => {
      version++
      clearTicker()
      scope.stop()
    },
  }
}
