import type { AgentReply, MapPoint } from './agent'
import type { TmsRow, VehiclePlan } from '../types/tms'

export type MapPlan = Pick<VehiclePlan, 'vehicleId' | 'vehicleName' | 'orderList' | 'routeList'>
export function agentMap(
  reply: AgentReply | null,
): { center: TmsRow; plans: MapPlan[] } | undefined {
  if (!reply?.result || !reply.map_data) return
  const { origin, stops } = reply.map_data
  const coordinate = (p: MapPoint) => `${p.lon},${p.lat}`
  const plans = reply.result.routes.map((route) => {
    const ordered = [...route.stops].sort((a, b) => a.sequence - b.sequence)
    return {
      vehicleId: route.vehicle_id,
      vehicleName: route.vehicle_id,
      orderList: ordered.map((stop) => ({
        orderId: stop.order_id,
        branchId: stop.destination_id,
        itemName: stop.order_id,
        address: stops[stop.order_id]!.matched_address,
        latitude: stops[stop.order_id]!.lat,
        longitude: stops[stop.order_id]!.lon,
        expectedArrivalTime: stop.eta?.slice(0, 16).replace(/\D/g, '') ?? '',
        expectedDepartureTime: '',
      })),
      routeList: ordered.length
        ? [{ route: [origin, ...ordered.map((s) => stops[s.order_id]!)].map(coordinate).join('|') }]
        : [],
    }
  })
  return {
    center: {
      centerName: '출발 센터',
      address: origin.matched_address,
      latitude: origin.lat,
      longitude: origin.lon,
    },
    plans,
  }
}
