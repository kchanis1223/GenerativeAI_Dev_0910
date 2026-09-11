import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import {
  readCsv,
  readDeliveryDataset,
  readDeliveryOrdersCsv,
} from '../../src/services/delivery-csv'
import { executeTms } from '../../src/services/tms-mock'
import { validateResponse } from '../../src/services/centers'
const file = (name: string) => readFileSync(new URL(`../../data/${name}`, import.meta.url), 'utf8')
const sources = {
  centers: file('centers.csv'),
  branches: file('branches.csv'),
  vehicles: file('vehicles.csv'),
  orders: file('delivery_orders.csv'),
}
const date = '2026-09-11'
function change(source: string, field: string, value: string) {
  const rows = readCsv(source),
    header = Object.keys(rows[0]!)
  rows[0]![field] = value
  const quote = (value: string) => `"${value.replaceAll('"', '""')}"`
  return [header, ...rows.map((row) => header.map((key) => row[key]!))]
    .map((row) => row.map(quote).join(','))
    .join('\n')
}

describe('노량진 당일 배송 CSV', () => {
  it('센터 1곳·서로 다른 서울 주소 20곳·차량 5대를 담는다', () => {
    const { state, branches } = readDeliveryDataset(sources, date)
    expect(state.centers).toHaveLength(1)
    expect(state.centers[0]).toMatchObject({
      centerName: '노량진센터',
      address: '서울특별시 동작구 노들로 674',
    })
    expect(branches).toHaveLength(20)
    expect(new Set(branches.map((b) => b.address)).size).toBe(20)
    expect(branches.every((b) => String(b.address).startsWith('서울특별시 '))).toBe(true)
    expect(branches.every((b) => String(b.branchName).startsWith('바다로 '))).toBe(true)
    expect(state.vehicles).toHaveLength(5)
    expect(state.vehicles.filter((v) => v.vehicleClass === '활어차')).toHaveLength(2)
    expect(state.vehicles.filter((v) => v.vehicleClass === '냉장차')).toHaveLength(2)
    expect(state.vehicles.filter((v) => v.vehicleClass === '일반차')).toHaveLength(1)
    expect(state.vehicles.every((v) => v.maxLoadKg === Number(v.weight) * 1000)).toBe(true)
  })
  it('지점별 2건·품목별 10건·총 3125kg과 납품 희망시간을 보존한다', () => {
    const { state, branches } = readDeliveryDataset(sources, date)
    expect(state.orders).toHaveLength(40)
    for (const branch of branches)
      expect(state.orders.filter((o) => o.branchId === branch.branchId)).toHaveLength(2)
    for (const category of ['활어', '냉장', '냉동', '일반']) {
      const orders = state.orders.filter((o) => o.itemType === category)
      expect(orders).toHaveLength(10)
      const capacity = state.vehicles
        .filter((v) => String(v.supportedItemTypes).split('|').includes(category))
        .reduce((sum, v) => sum + Number(v.maxLoadKg), 0)
      expect(orders.reduce((sum, o) => sum + Number(o.deliveryWeight), 0)).toBeLessThanOrEqual(
        capacity,
      )
    }
    expect(state.orders.reduce((sum, o) => sum + Number(o.deliveryWeight), 0)).toBe(3125)
    expect(state.orders.every((o) => o.deliveryDate === date && o.desiredDeliveryTime)).toBe(true)
    expect(readDeliveryOrdersCsv(sources.orders, '2026-09-12')).toEqual([])
  })
  it('필드명을 바꾸지 않고 기존 /orderList·/vehicleList·/centerList 목업이 읽는다', () => {
    const { state } = readDeliveryDataset(sources, date)
    const response = executeTms(state, '/orderList')
    expect(response).toMatchObject({ resultCode: '200', resultCount: 40 })
    expect(response.resultData).toEqual(state.orders)
    expect(state.orders.find((o) => o.itemType === '냉장')?.vehicleType).toBe('02')
    expect(state.orders.find((o) => o.itemType === '일반')?.vehicleType).toBe('01')
    expect(state.orders[0]).toMatchObject({
      deliveryWeight: expect.any(Number),
      latitude: expect.any(Number),
      longitude: expect.any(Number),
      openTime: expect.any(String),
      itemType: '활어',
    })
    expect(executeTms(state, '/vehicleList').resultCount).toBe(5)
    expect(validateResponse(executeTms(state, '/centerList')).resultCount).toBe(1)
  })
  it('센터와 지점 21곳은 실제 응답의 도로명·건물번호·구·도시 및 좌표와 일치한다', () => {
    const proof = readCsv(file('geocoding_results.csv'))
    const { state, branches } = readDeliveryDataset(sources)
    expect(proof).toHaveLength(21)
    expect(proof.filter((r) => r.entityType === 'branch')).toHaveLength(20)
    expect(new Set(proof.map((r) => r.entityId)).size).toBe(21)
    for (const row of [...state.centers, ...branches]) {
      const id = row.branchId ?? row.centerId
      const evidence = proof.find((p) => p.entityId === id)!
      expect(evidence, String(id)).toBeDefined()
      expect(evidence.status).toBe('SUCCESS_EXACT_ADDRESS')
      expect(evidence.httpStatus).toBe('200')
      expect(evidence.queryAddress).toBe(row.address)
      expect(new URL(evidence.requestUrl!).searchParams.get('q')).toBe(row.address)
      expect(Number(evidence.latitude)).toBe(row.latitude)
      expect(Number(evidence.longitude)).toBe(row.longitude)
      const raw = JSON.parse(evidence.rawResponse!) as Record<string, unknown>[]
      const match = raw.find(
        (r) => String(r.osm_id) === evidence.osmId && r.osm_type === evidence.osmType,
      )!
      const [city, borough, road, house_number] = String(row.address).split(' ')
      expect(match.address).toMatchObject({ city, borough, road, house_number, country_code: 'kr' })
      expect(match.place_rank).toBe(30)
      expect(Number(match.lat)).toBe(row.latitude)
      expect(Number(match.lon)).toBe(row.longitude)
      expect(Number(row.latitude)).toBeGreaterThan(37.4)
      expect(Number(row.latitude)).toBeLessThan(37.7)
      expect(Number(row.longitude)).toBeGreaterThan(126.7)
      expect(Number(row.longitude)).toBeLessThan(127.2)
      expect(evidence.checkedAt).toMatch(/^2026-09-11T/)
      expect(evidence.addressSource).toMatch(/^https:\/\//)
    }
  })
  it('도로 대표점만 반환한 주소 4곳은 최종 데이터에 섞이지 않는다', () => {
    const rejected = readCsv(file('geocoding_rejected.csv'))
    const { branches } = readDeliveryDataset(sources)
    expect(rejected).toHaveLength(4)
    for (const r of rejected) {
      expect(branches.some((b) => b.address === r.queryAddress)).toBe(false)
      const raw = JSON.parse(r.rawResponse!) as {
        place_rank: number
        address: { house_number?: string }
      }[]
      expect(raw.every((r) => r.place_rank < 30 && !r.address.house_number)).toBe(true)
    }
  })
  it('BOM·쉼표·따옴표·줄바꿈을 보존하고 잘못된 CSV는 거부한다', () => {
    expect(readCsv('\uFEFFid,name,note\r\n01,"가상, 지점","첫 줄\n""둘째"" 줄"\r\n')).toEqual([
      { id: '01', name: '가상, 지점', note: '첫 줄\n"둘째" 줄' },
    ])
    expect(() => readCsv('id,id\n1,2')).toThrow('헤더')
    expect(() => readCsv('id,name\n1')).toThrow('컬럼')
    expect(() => readCsv('id,name\n1,"가상')).toThrow('따옴표')
  })
  it('비정상 중량·시간창·차종·참조·적재 단위를 거부한다', () => {
    expect(() => readDeliveryOrdersCsv(change(sources.orders, 'deliveryWeight', '-1'))).toThrow(
      '중량',
    )
    expect(() =>
      readDeliveryOrdersCsv(change(sources.orders, 'desiredDeliveryTime', '25:00')),
    ).toThrow('희망시간')
    expect(() => readDeliveryOrdersCsv(change(sources.orders, 'closeTime', '0800'))).toThrow(
      '시간창',
    )
    expect(() => readDeliveryOrdersCsv(change(sources.orders, 'vehicleType', '01'))).toThrow('품목')
    expect(() =>
      readDeliveryDataset({ ...sources, orders: change(sources.orders, 'branchId', 'missing') }),
    ).toThrow('지점')
    expect(() =>
      readDeliveryDataset({ ...sources, vehicles: change(sources.vehicles, 'maxLoadKg', '2') }),
    ).toThrow('단위')
  })
})
