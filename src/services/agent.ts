export const modeLabels = {
  offline: 'Python 합성 Mock · 제한된 예시 입력',
  llm_mock: 'LLM + Python 합성 Mock',
  live: '실제 API',
}
export type AgentMode = keyof typeof modeLabels
export interface MapPoint {
  lat: number
  lon: number
  matched_address: string
}
export interface AgentMapData {
  origin: MapPoint
  stops: Record<string, MapPoint>
}
export interface AgentResult {
  status: 'success' | 'partial' | 'failed'
  routes: {
    vehicle_id: string
    stops: { sequence: number; order_id: string; destination_id: string; eta: string | null }[]
    estimated_duration_seconds: number | null
    distance_meters: number | null
  }[]
  unassigned_orders: {
    order_id: string
    reason_code: string | null
    reason_message: string | null
  }[]
}
export interface AgentReply {
  thread_id: string
  request_id: string
  mode: AgentMode
  status: 'completed' | 'needs_clarification' | 'blocked' | 'error'
  message: string
  questions: string[]
  result: AgentResult | null
  map_data?: AgentMapData | null
  error: { code: string; message: string; retryable: boolean } | null
}
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object'
const strings = (v: unknown): v is string[] =>
  Array.isArray(v) && v.every((s) => typeof s === 'string')
const nullableString = (v: unknown) => v === null || typeof v === 'string'
const nullableNumber = (v: unknown) =>
  v === null || (typeof v === 'number' && Number.isFinite(v) && v >= 0)
export function isMode(v: unknown): v is AgentMode {
  return typeof v === 'string' && Object.hasOwn(modeLabels, v)
}
export function parseReply(v: unknown): AgentReply {
  if (
    !record(v) ||
    typeof v.thread_id !== 'string' ||
    typeof v.request_id !== 'string' ||
    !isMode(v.mode) ||
    !['completed', 'needs_clarification', 'blocked', 'error'].includes(String(v.status)) ||
    typeof v.message !== 'string' ||
    !strings(v.questions) ||
    !(
      v.error === null ||
      (record(v.error) &&
        typeof v.error.code === 'string' &&
        typeof v.error.message === 'string' &&
        typeof v.error.retryable === 'boolean')
    )
  )
    throw new Error('에이전트 응답 형식을 확인할 수 없습니다.')
  const r = v.result
  if (
    r !== null &&
    (!record(r) ||
      !['success', 'partial', 'failed'].includes(String(r.status)) ||
      !Array.isArray(r.routes) ||
      !r.routes.every(
        (route: unknown) =>
          record(route) &&
          typeof route.vehicle_id === 'string' &&
          nullableNumber(route.estimated_duration_seconds) &&
          nullableNumber(route.distance_meters) &&
          Array.isArray(route.stops) &&
          route.stops.every(
            (stop: unknown) =>
              record(stop) &&
              Number.isInteger(stop.sequence) &&
              Number(stop.sequence) >= 1 &&
              typeof stop.order_id === 'string' &&
              typeof stop.destination_id === 'string' &&
              nullableString(stop.eta),
          ),
      ) ||
      !Array.isArray(r.unassigned_orders) ||
      !r.unassigned_orders.every(
        (o: unknown) =>
          record(o) &&
          typeof o.order_id === 'string' &&
          nullableString(o.reason_code) &&
          nullableString(o.reason_message),
      ))
  )
    throw new Error('배차 결과 형식을 확인할 수 없습니다.')
  const point = (p: unknown): p is MapPoint =>
    record(p) &&
    typeof p.lat === 'number' &&
    Number.isFinite(p.lat) &&
    Math.abs(p.lat) <= 90 &&
    typeof p.lon === 'number' &&
    Number.isFinite(p.lon) &&
    Math.abs(p.lon) <= 180 &&
    typeof p.matched_address === 'string'
  const map = v.map_data
  if (
    map != null &&
    (!record(map) ||
      !point(map.origin) ||
      !record(map.stops) ||
      !Object.values(map.stops).every(point) ||
      !r ||
      !(r as unknown as AgentResult).routes.every((route) =>
        route.stops.every((stop) => Object.hasOwn(map.stops as object, stop.order_id)),
      ))
  )
    throw new Error('배차 지도 좌표를 확인할 수 없습니다.')
  return v as unknown as AgentReply
}
export async function agentHealth(): Promise<AgentMode> {
  const response = await fetch('/api/agent/health', { signal: AbortSignal.timeout(5000) })
  const data: unknown = await response.json()
  if (!response.ok || !record(data) || data.status !== 'ok' || !isMode(data.mode))
    throw new Error('에이전트 서버 연결을 확인해 주세요.')
  return data.mode
}
export async function sendAgentMessage(message: string, threadId?: string): Promise<AgentReply> {
  const response = await fetch('/api/agent/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, ...(threadId ? { thread_id: threadId } : {}) }),
    signal: AbortSignal.timeout(180000),
  })
  if (!response.ok)
    throw new Error(`에이전트 요청 실패 (HTTP ${response.status}). 서버 상태를 확인해 주세요.`)
  return parseReply(await response.json())
}
