import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockCenters } from '../fixtures/centers'
import { requestCenters, validateProxyEndpoint, validateResponse } from '../../src/services/centers'

const valid = () => ({
  resultCode: '200',
  resultCount: mockCenters.length,
  resultMessage: 'success',
  resultData: structuredClone(mockCenters),
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('센터 응답 검증', () => {
  it('명세의 필드를 보존한다', () => {
    expect(validateResponse(valid()).resultData).toEqual(mockCenters)
  })
  it('빈 응답은 정상 결과로 처리한다', () => {
    expect(validateResponse({ ...valid(), resultCount: 0, resultData: [] }).resultData).toEqual([])
  })
  it('비정상 상태 코드와 손상된 응답은 결과로 사용하지 않는다', () => {
    expect(() => validateResponse({ ...valid(), resultCode: '401' })).toThrow('실패 응답')
    expect(() => validateResponse({ ...valid(), resultCode: 200 })).toThrow('문자열')
    expect(() => validateResponse({ ...valid(), resultCount: 999 })).toThrow('개수')
    expect(() => validateResponse({ ...valid(), resultData: [null] })).toThrow('객체')
    const response = valid()
    response.resultData[0]!.latitude = 91
    expect(() => validateResponse(response)).toThrow('좌표')
    response.resultData[0]!.latitude = 37
    response.resultData[1]!.centerId = response.resultData[0]!.centerId
    expect(() => validateResponse(response)).toThrow('중복')
  })
  it.each([
    'https://example.com/api',
    '//example.com/api',
    '/api/../secret',
    '/api/test?appKey=secret',
    '/api/\\external',
  ])('잘못된 프록시 경로를 거부한다: %s', (url) => {
    expect(() => validateProxyEndpoint(url)).toThrow()
  })
})

describe('실제 API 연결 어댑터', () => {
  it('서버 프록시에서 받은 데이터를 반환하고 브라우저에 앱 키를 요구하지 않는다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(valid())))
    vi.stubGlobal('fetch', fetchMock)
    const result = await requestCenters('/api/tms/centerList')
    expect(validateResponse(result).resultCount).toBe(8)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/tms/centerList',
      expect.objectContaining({ headers: { Accept: 'application/json' } }),
    )
  })
  it('HTTP 401을 목업으로 대체하지 않고 오류를 반환한다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })))
    await expect(requestCenters('/api/tms/centerList')).rejects.toMatchObject({ code: '401' })
  })
  it('설정되지 않은 경로가 HTML을 반환하면 연결 오류를 안내한다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<!doctype html>')))
    await expect(requestCenters('/api/tms/centerList')).rejects.toMatchObject({
      code: 'INVALID_JSON',
    })
  })
  it('8초 후 실제 네트워크 요청을 중단한다', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener('abort', () =>
              reject(new DOMException('Aborted', 'AbortError')),
            )
          }),
      ),
    )
    const request = requestCenters('/api/tms/centerList')
    const assertion = expect(request).rejects.toMatchObject({ code: 'TIMEOUT' })
    await vi.advanceTimersByTimeAsync(8000)
    await assertion
  })
})
