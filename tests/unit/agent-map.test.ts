import { expect, it } from 'vitest'
import { parseReply } from '../../src/services/agent'
import { agentMap } from '../../src/services/agent-map'

const point = (lat: number, lon: number) => ({ lat, lon, matched_address: '확정 주소' })
const reply = {
  thread_id: 'thread',
  request_id: 'request',
  mode: 'live',
  status: 'completed',
  message: '일부 배차',
  questions: [],
  error: null,
  result: {
    status: 'partial',
    unassigned_orders: [{ order_id: 'missing', reason_code: null, reason_message: null }],
    routes: [
      {
        vehicle_id: 'V1',
        distance_meters: null,
        estimated_duration_seconds: null,
        stops: [
          { sequence: 2, order_id: 'B', destination_id: 'S2', eta: null },
          { sequence: 1, order_id: 'A', destination_id: 'S1', eta: '2026-09-12T06:25:00+09:00' },
        ],
      },
    ],
  },
  map_data: { origin: point(37.5, 126.9), stops: { A: point(37.6, 127), B: point(37.7, 127.1) } },
}
it('서버 좌표를 방문 순서로 연결하고 미배정·누락 ETA를 생성하지 않는다', () => {
  const plan = agentMap(parseReply(reply))!.plans[0]!
  expect(plan.routeList[0]!.route).toBe('126.9,37.5|127,37.6|127.1,37.7')
  expect(plan.orderList.map((o) => o.orderId)).toEqual(['A', 'B'])
  expect(plan.orderList.map((o) => o.expectedArrivalTime)).toEqual(['202609120625', ''])
  expect(reply.result.routes[0]!.stops[0]!.order_id).toBe('B')
  expect(agentMap(parseReply({ ...reply, map_data: null }))).toBeUndefined()
  expect(agentMap(null)).toBeUndefined()
})
it.each([
  { ...reply.map_data, stops: { A: point(37.6, 127) } },
  { ...reply.map_data, origin: point(91, 127) },
  { ...reply.map_data, origin: point(37, Infinity) },
])('불완전하거나 잘못된 지도 좌표를 거부한다', (map_data) => {
  expect(() => parseReply({ ...reply, map_data })).toThrow('지도 좌표')
})
