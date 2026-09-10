import { tmsState } from '../stores/tms'
import type { Center, CenterResponse, Connection, Scenario } from '../types'

export const API_REFERENCE = 'https://tms-skopenapi.readme.io/reference/센터-목록조회'
export const API_URL = 'https://apis.openapi.sk.com/tms/centerList'
export const REQUEST_TIMEOUT = 8000
export const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export class CenterApiError extends Error {
  constructor(
    message: string,
    public code: string,
  ) {
    super(message)
    this.name = 'CenterApiError'
  }
}

export function validateResponse(value: unknown): CenterResponse {
  if (!value || typeof value !== 'object')
    throw new CenterApiError('응답이 JSON 객체가 아닙니다.', 'SCHEMA_ERROR')
  const data = value as Record<string, unknown>
  if (typeof data.resultCode !== 'string')
    throw new CenterApiError('resultCode는 문자열이어야 합니다.', 'SCHEMA_ERROR')
  if (data.resultCode !== '200')
    throw new CenterApiError(
      `API가 실패 응답을 반환했습니다. (${data.resultCode})`,
      data.resultCode,
    )
  if (
    !Number.isInteger(data.resultCount) ||
    typeof data.resultCount !== 'number' ||
    data.resultCount < 0 ||
    typeof data.resultMessage !== 'string' ||
    !Array.isArray(data.resultData)
  ) {
    throw new CenterApiError('응답의 필수 필드 또는 데이터 타입이 명세와 다릅니다.', 'SCHEMA_ERROR')
  }
  for (const item of data.resultData) {
    if (!item || typeof item !== 'object')
      throw new CenterApiError('센터 데이터가 객체가 아닙니다.', 'SCHEMA_ERROR')
    const c = item as Record<string, unknown>
    if (
      ['centerId', 'centerName', 'address', 'updateDate'].some(
        (key) => typeof c[key] !== 'string',
      ) ||
      !c.centerId ||
      !c.centerName ||
      !Number.isInteger(c.seq) ||
      typeof c.latitude !== 'number' ||
      !Number.isFinite(c.latitude) ||
      Math.abs(c.latitude) > 90 ||
      typeof c.longitude !== 'number' ||
      !Number.isFinite(c.longitude) ||
      Math.abs(c.longitude) > 180
    ) {
      throw new CenterApiError('센터 필드 또는 좌표가 유효하지 않습니다.', 'SCHEMA_ERROR')
    }
  }
  const ids = data.resultData.map((c: Center) => c.centerId)
  if (new Set(ids).size !== ids.length || data.resultCount !== data.resultData.length) {
    throw new CenterApiError(
      '센터 ID가 중복되거나 resultCount가 실제 개수와 다릅니다.',
      'SCHEMA_ERROR',
    )
  }
  return data as unknown as CenterResponse
}

export function filterCenters(centers: Center[], query: string, region: string): Center[] {
  const normalized = query.trim().toLocaleLowerCase('ko-KR')
  return centers.filter(
    (center) =>
      (region === '전체' || center.address.startsWith(region)) &&
      (!normalized ||
        `${center.centerName} ${center.centerId} ${center.address}`
          .toLocaleLowerCase('ko-KR')
          .includes(normalized)),
  )
}

// appKey is added by a future server proxy, never by the browser bundle.
export function validateProxyEndpoint(endpoint: string): string {
  const normalized = endpoint.trim()
  if (!normalized.startsWith('/api/') || /[\\?#\s]/.test(normalized) || normalized.includes('..')) {
    throw new CenterApiError(
      '같은 출처의 /api/로 시작하는 프록시 경로를 입력하세요.',
      'CONFIG_ERROR',
    )
  }
  return normalized
}

export async function requestCenters(
  connection: Connection,
  scenario: Scenario = 'success',
): Promise<unknown> {
  if (connection.mode === 'mock') {
    await wait(scenario === 'timeout' ? 1400 : 650)
    if (scenario === 'unauthorized')
      throw new CenterApiError('인증에 실패했습니다. 연결 서버의 appKey를 확인하세요.', '401')
    if (scenario === 'timeout')
      throw new CenterApiError('요청 시간이 초과되었습니다. 잠시 후 다시 실행하세요.', 'TIMEOUT')
    if (scenario === 'invalid')
      return {
        resultCode: '200',
        resultCount: 1,
        resultMessage: 'success',
        resultData: [{ centerId: 'invalid_demo' }],
      }
    const centers = scenario === 'empty' ? [] : tmsState.centers.map((c) => ({ ...c }))
    return {
      resultCode: '200',
      resultCount: centers.length,
      resultMessage: 'success',
      resultData: centers,
    }
  }
  const endpoint = validateProxyEndpoint(connection.endpoint)
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)
  try {
    const response = await fetch(endpoint, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
      credentials: 'same-origin',
      redirect: 'error',
    })
    if (!response.ok)
      throw new CenterApiError(
        response.status === 401
          ? '인증에 실패했습니다. 연결 서버의 appKey를 확인하세요.'
          : `API 요청에 실패했습니다. (HTTP ${response.status})`,
        String(response.status),
      )
    try {
      return await response.json()
    } catch {
      throw new CenterApiError(
        '서버가 JSON을 반환하지 않았습니다. 프록시 경로를 확인하세요.',
        'INVALID_JSON',
      )
    }
  } catch (error) {
    if (error instanceof CenterApiError) throw error
    if (controller.signal.aborted)
      throw new CenterApiError('요청 시간이 초과되었습니다. 잠시 후 다시 실행하세요.', 'TIMEOUT')
    throw new CenterApiError(
      '서버에 연결할 수 없습니다. 프록시 연결을 확인하세요.',
      'NETWORK_ERROR',
    )
  } finally {
    clearTimeout(timer)
  }
}
