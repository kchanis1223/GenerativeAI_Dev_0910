import { expect, it } from 'vitest'
import { createDispatchConsole } from '../../src/stores/dispatch-console'
import type { AgentReply } from '../../src/services/agent'

function reply(): AgentReply {
  return {
    thread_id: 'demo',
    request_id: 'req',
    status: 'completed',
    mode: 'offline',
    message: '일부 미배정',
    questions: [],
    error: null,
    request: {
      depot_id: 'CENTER-NR',
      delivery_date: '2026-09-11',
      departure_time: '2026-09-11T06:00:00+09:00',
    },
    presentation: {
      scenario: 'M06',
      source: '고정 시연',
      vehicle_ids: ['LIVE01'],
      candidates: [],
      audit: { allocation_calls: 1, poll_calls: 0, communication_retries: 0 },
      orders: [
        {
          order_id: 'ORD-20260911-001',
          destination_id: 'S01',
          address: '확정 주소',
          weight_kg: 80,
          volume_m3: null,
          service_seconds: 600,
          items: [{ product_name: '활광어', weight_kg: 80 }],
          coordinate: { lat: 37.5, lon: 126.9 },
        },
      ],
    },
    result: {
      status: 'partial',
      routes: [
        {
          vehicle_id: 'LIVE01',
          distance_meters: null,
          estimated_duration_seconds: null,
          stops: [{ sequence: 1, order_id: 'ORD-20260911-001', destination_id: 'S01', eta: null }],
        },
      ],
      unassigned_orders: [
        { order_id: 'unassigned', reason_code: 'capacity', reason_message: '적재량 초과' },
      ],
    },
  }
}
it('현재 Python 주문과 좌표를 선택·표·경로로 변환하고 없는 지표를 보존한다', () => {
  const c = createDispatchConsole()
  c.applyAgentReply(reply())
  expect(c.state.orderIds).toEqual(['ORD-20260911-001'])
  expect(c.state.startTime).toBe('06:00')
  expect(c.state.result!.vehicleList[0]).toMatchObject({
    deliveryTime: null,
    deliveryDistance: null,
    orderList: [{ address: '확정 주소', latitude: 37.5, expectedArrivalTime: '' }],
  })
  expect(c.state.result!.vehicleList[0]!.routeList[0]!.route).toContain('126.9,37.5')
  expect(c.state.result!.mock.unassigned[0]!.reason).toContain('적재량 초과')
  c.dispose()
})
it('새 요청의 좌표가 미확정이면 이전 지도 좌표를 재사용하지 않는다', () => {
  const c = createDispatchConsole()
  c.applyAgentReply(reply())
  const next = reply()
  next.presentation!.orders[0]!.coordinate = null
  c.applyAgentReply(next)
  expect(c.state.result).toBeNull()
  expect(c.state.visibleVehicleIds).toEqual([])
  expect(c.state.error).toContain('확정된 배송 좌표')
  c.dispose()
})
it('수동 선택과 새 대화는 에이전트 결과를 초기화한다', () => {
  const c = createDispatchConsole()
  c.applyAgentReply(reply())
  c.state.orderIds = []
  expect(c.state.result).toBeNull()
  expect(c.state.agentSource).toBe('')
  c.applyAgentReply(reply())
  c.clearAgent()
  expect(c.state.result).toBeNull()
  expect(c.state.orderIds).toEqual([])
  c.dispose()
})
