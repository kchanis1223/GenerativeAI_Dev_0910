import type { Resource, TmsRow } from '../types/tms'

export const resources: Record<
  Resource,
  { title: string; singular: string; prefix: string; id: string; name: string }
> = {
  centers: {
    title: '센터 정보',
    singular: '센터',
    prefix: 'center',
    id: 'centerId',
    name: 'centerName',
  },
  zones: { title: '권역 정보', singular: '권역', prefix: 'zone', id: 'code', name: 'name' },
  vehicles: {
    title: '차량 정보',
    singular: '차량',
    prefix: 'vehicle',
    id: 'vehicleId',
    name: 'vehicleName',
  },
  orders: {
    title: '배송지 정보',
    singular: '배송지',
    prefix: 'order',
    id: 'orderId',
    name: 'orderName',
  },
  banLines: {
    title: '교차금지선',
    singular: '교차금지선',
    prefix: 'banLine',
    id: 'seq',
    name: 'lineName',
  },
}
const sampleDate = '2026-09-10 09:00:00'
export function newVehicle(id: string, name: string, overrides: TmsRow = {}): TmsRow {
  return {
    vehicleId: id,
    vehicleName: name,
    weight: 1,
    volume: 8,
    vehicleType: '01',
    zoneCode: '0001',
    inputYn: '1',
    skillPer: 100,
    startAddress: '',
    startLatitude: 0,
    startLongitude: 0,
    endAddress: '',
    endLatitude: 0,
    endLongitude: 0,
    speed: 0,
    costPerHour: 0,
    costPerKm: 0,
    waitcostPerHour: 0,
    updateDate: sampleDate,
    seq: 0,
    ...overrides,
  }
}
export function newOrder(id: string, name: string, overrides: TmsRow = {}): TmsRow {
  return {
    orderId: id,
    orderName: name,
    address: '서울특별시 마포구 독막로 291',
    latitude: 37.54468,
    longitude: 126.945455,
    vehicleType: '01',
    zoneCode: '0001',
    deliveryWeight: 250,
    deliveryVolume: 1,
    serviceTime: 10,
    deliveryCount: 0,
    openTime: '',
    closeTime: '',
    adminCode: '',
    postCode: '',
    updateDate: sampleDate,
    seq: 0,
    ...overrides,
  }
}
