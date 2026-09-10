import { mockCenters } from './centers'
import type { Resource, TmsRow, TmsState } from '../types/tms'

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
export function createTmsState(): TmsState {
  return {
    centers: mockCenters.map((c) => ({ ...c })),
    zones: [
      {
        code: '0001',
        name: '서울 도심권',
        zipcodeData: '',
        adminData: '',
        updateDate: sampleDate,
        seq: 243,
      },
      {
        code: '0002',
        name: '경기 남부권',
        zipcodeData: '',
        adminData: '',
        updateDate: sampleDate,
        seq: 244,
      },
      {
        code: '0003',
        name: '인천권',
        zipcodeData: '',
        adminData: '',
        updateDate: sampleDate,
        seq: 245,
      },
    ],
    vehicles: [
      newVehicle('vehicle01', '12가1234', { weight: 1, volume: 8, seq: 557 }),
      newVehicle('vehicle02', '56너5678', { weight: 2, volume: 12, seq: 558 }),
      newVehicle('vehicle03', '서울 냉장 01', {
        vehicleType: '02',
        weight: 1,
        volume: 6,
        seq: 559,
      }),
      newVehicle('vehicle04', '경기 배송 01', {
        zoneCode: '0002',
        weight: 3,
        volume: 18,
        seq: 560,
      }),
      newVehicle('vehicle05', '정비 대기 차량', { inputYn: '0', weight: 5, seq: 561 }),
      newVehicle('vehicle06', '신규 배송 차량', { skillPer: 70, weight: 1, volume: 5, seq: 562 }),
    ],
    orders: [
      newOrder('order01', '마포지점01', { seq: 18700 }),
      newOrder('order02', '성수지점', {
        address: '서울특별시 성동구 아차산로 113',
        latitude: 37.5446,
        longitude: 127.056,
        deliveryWeight: 400,
        deliveryVolume: 2,
        serviceTime: 15,
        seq: 18701,
      }),
      newOrder('order03', '강남 냉장지점', {
        address: '서울특별시 강남구 테헤란로 152',
        latitude: 37.5001,
        longitude: 127.0365,
        vehicleType: '02',
        deliveryWeight: 600,
        deliveryVolume: 3,
        seq: 18702,
      }),
      newOrder('order04', '을지로지점', {
        address: '서울특별시 중구 을지로 65',
        latitude: 37.566482,
        longitude: 126.985085,
        deliveryWeight: 350,
        seq: 18703,
      }),
      newOrder('order05', '안산지점01', {
        address: '경기도 안산시 단원구 와동',
        latitude: 37.332643,
        longitude: 126.819828,
        zoneCode: '0002',
        deliveryWeight: 800,
        deliveryVolume: 4,
        seq: 18704,
      }),
      newOrder('order06', '분당지점', {
        address: '경기도 성남시 분당구 판교역로 235',
        latitude: 37.4009,
        longitude: 127.1081,
        zoneCode: '0002',
        deliveryWeight: 600,
        deliveryVolume: 3,
        seq: 18705,
      }),
      newOrder('order07', '종로지점', {
        address: '서울특별시 종로구 종로 1',
        latitude: 37.5705,
        longitude: 126.979,
        deliveryWeight: 450,
        deliveryVolume: 2,
        seq: 18706,
      }),
      newOrder('order08', '인천 미배차 예제', {
        address: '인천광역시 연수구 센트럴로 123',
        latitude: 37.389,
        longitude: 126.644,
        zoneCode: '0003',
        deliveryWeight: 1200,
        deliveryVolume: 6,
        seq: 18707,
      }),
    ],
    banLines: [
      {
        seq: 124,
        lineName: '동부 통제구간 · 예제',
        lineData: '127.20,37.70_127.20,37.75',
        updateDate: sampleDate,
      },
    ],
    jobs: {},
    nextSeq: 20000,
  }
}
