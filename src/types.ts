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
