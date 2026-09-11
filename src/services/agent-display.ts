import type { AgentReply, Presentation } from './agent'
import type { DispatchResult, TmsState, VehiclePlan, AssignedOrder } from '../types/tms'

// Only coordinates confirmed within this request may be drawn; never fill from another request.
export function agentDisplay(reply: AgentReply, data: TmsState): DispatchResult | null {
  if (!reply.result) return null
  const p = reply.presentation
  if (!p || !reply.request) throw new Error('요청별 좌표와 주문 정보가 없습니다.')
  const center = data.centers.find((c) => c.centerId === reply.request!.depot_id)
  if (!center) throw new Error('출발 센터를 확인할 수 없습니다.')
  const location = {
    address: String(center.address),
    latitude: String(center.latitude),
    longitude: String(center.longitude),
  }
  const rows = new Map(p.orders.map((o) => [o.order_id, o]))
  const vehicleList: VehiclePlan[] = reply.result.routes.map((route) => {
    const orderList: AssignedOrder[] = route.stops.map((stop) => {
      const o = rows.get(stop.order_id)
      if (
        !o ||
        o.destination_id !== stop.destination_id ||
        !o.coordinate ||
        !Number.isFinite(o.coordinate.lat) ||
        Math.abs(o.coordinate.lat) > 90 ||
        !Number.isFinite(o.coordinate.lon) ||
        Math.abs(o.coordinate.lon) > 180
      )
        throw new Error('현재 요청에서 확정된 배송 좌표가 없습니다.')
      return {
        orderId: o.order_id,
        branchId: o.destination_id,
        address: o.address,
        orderName: `${o.destination_id} · ${o.items.map((i) => i.product_name).join(', ')}`,
        itemName: o.items.map((i) => i.product_name).join(', '),
        latitude: o.coordinate.lat,
        longitude: o.coordinate.lon,
        deliveryWeight: o.weight_kg,
        deliveryVolume: o.volume_m3 ?? 0,
        serviceTime: o.service_seconds / 60,
        desiredDeliveryTime: '미제공',
        expectedArrivalTime: stop.eta ?? '',
        expectedDepartureTime: '',
        sequence: stop.sequence,
      }
    })
    const points = [location, ...orderList]
    return {
      vehicleId: route.vehicle_id,
      vehicleName: String(
        data.vehicles.find((v) => v.vehicleId === route.vehicle_id)?.vehicleName ??
          route.vehicle_id,
      ),
      deliveryCount: orderList.length,
      deliveryTime: route.estimated_duration_seconds,
      deliveryDistance: route.distance_meters,
      deliveryWeight: orderList.reduce((sum, o) => sum + Number(o.deliveryWeight), 0),
      deliveryVolume: orderList.reduce((sum, o) => sum + Number(o.deliveryVolume), 0),
      orderList,
      startLocation: location,
      endLocation: orderList.length
        ? {
            address: String(orderList.at(-1)!.address),
            latitude: String(orderList.at(-1)!.latitude),
            longitude: String(orderList.at(-1)!.longitude),
          }
        : location,
      routeList: [{ route: points.map((o) => `${o.longitude},${o.latitude}`).join('|') }],
    }
  })
  return {
    resultCode: '200',
    resultMessage: reply.message,
    vehicleCount: String(vehicleList.length),
    vehicleList,
    mock: {
      simulated: true,
      routing: p.source + ' · 확정 좌표 간 직선, 실제 도로 경로 아님',
      assumptions: ['ETA·거리·시간 미제공 값 유지'],
      unassigned: reply.result.unassigned_orders.map((o) => ({
        orderId: o.order_id,
        orderName: o.order_id,
        reason: [o.reason_code, o.reason_message].filter(Boolean).join(' · ') || '사유 미제공',
      })),
    },
  }
}

export function assertPresentation(value: unknown): asserts value is Presentation {
  const p = value as Presentation
  if (
    !p ||
    typeof p.scenario !== 'string' ||
    typeof p.source !== 'string' ||
    !Array.isArray(p.orders) ||
    !Array.isArray(p.vehicle_ids) ||
    !p.vehicle_ids.every((v) => typeof v === 'string') ||
    !Array.isArray(p.candidates) ||
    !p.candidates.every((v) => typeof v === 'string') ||
    !p.audit ||
    !Object.values(p.audit).every((v) => Number.isInteger(v) && v >= 0) ||
    !p.orders.every(
      (o) =>
        typeof o.order_id === 'string' &&
        typeof o.destination_id === 'string' &&
        typeof o.address === 'string' &&
        Number.isFinite(o.weight_kg) &&
        Number.isFinite(o.service_seconds) &&
        Array.isArray(o.items) &&
        o.items.every((i) => typeof i.product_name === 'string') &&
        (o.coordinate === null ||
          (o.coordinate && Number.isFinite(o.coordinate.lat) && Number.isFinite(o.coordinate.lon))),
    )
  )
    throw new Error('시연 응답 형식을 확인할 수 없습니다.')
}
