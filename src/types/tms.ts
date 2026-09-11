export type Resource = 'centers' | 'zones' | 'vehicles' | 'orders' | 'banLines'
export type TmsRow = Record<string, string | number>
export type TmsPayload = Record<string, unknown>
export interface ApiParameter {
  name: string
  type: string
  required: boolean
  location: string
  description: string
  default: string
}
export interface ApiOperation {
  title: string
  slug: string
  source: string
  method: string
  path: string
  parameters: ApiParameter[]
  examples: { status: number; value: unknown }[]
}
export interface AssignedOrder extends TmsRow {
  orderId: string
  expectedArrivalTime: string
  expectedDepartureTime: string
}
export interface VehiclePlan {
  vehicleId: string
  vehicleName: string
  deliveryCount: number
  deliveryTime: number
  deliveryDistance: number
  deliveryWeight: number
  deliveryVolume: number
  orderList: AssignedOrder[]
  startLocation: { address: string; latitude: string; longitude: string }
  endLocation: { address: string; latitude: string; longitude: string }
  routeList: { route: string }[]
}
export interface DispatchResult {
  resultCode: string
  resultMessage: string
  vehicleCount: string
  vehicleList: VehiclePlan[]
  vehicleRouteList?: VehiclePlan[]
  mock: {
    simulated: true
    routing: string
    unassigned: { orderId: string; orderName: string; reason: string }[]
    assumptions: string[]
  }
}
export interface AllocationJob {
  readyAt: number
  result: DispatchResult
}
export interface TmsState {
  centers: TmsRow[]
  zones: TmsRow[]
  vehicles: TmsRow[]
  orders: TmsRow[]
  banLines: TmsRow[]
  jobs: Record<string, AllocationJob>
  nextSeq: number
}
export interface TmsLog {
  id: string
  time: string
  path: string
  title: string
  method: string
  request: TmsPayload
  mockContext?: MockContext
  response: unknown
  status: 'success' | 'pending' | 'error'
  duration: number
}

export interface MockContext {
  centerId?: string
}
