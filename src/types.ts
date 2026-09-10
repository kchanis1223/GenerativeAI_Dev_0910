export interface Center {
  centerId: string
  updateDate: string
  address: string
  latitude: number
  seq: number
  centerName: string
  longitude: number
}

export interface CenterResponse {
  resultCode: string
  resultCount: number
  resultMessage: string
  resultData: Center[]
}

export type Scenario = 'success' | 'empty' | 'unauthorized' | 'timeout' | 'invalid'
export type DataMode = 'mock' | 'proxy'
export interface Connection {
  mode: DataMode
  endpoint: string
}
export interface TraceStep {
  title: string
  description: string
  status: 'pending' | 'running' | 'success' | 'error'
  detail: string
}
export interface RunRecord {
  id: number
  time: string
  query: string
  region: string
  mode: DataMode
  scenario: Scenario
  status: 'success' | 'error'
  duration: number
  count: number
  message: string
}
