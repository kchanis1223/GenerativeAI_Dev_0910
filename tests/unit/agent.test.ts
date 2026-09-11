import { describe, expect, it, vi, afterEach } from 'vitest'
import { parseReply, sendAgentMessage } from '../../src/services/agent'

const reply = {
  thread_id: 'thread',
  request_id: 'request',
  mode: 'offline',
  status: 'blocked',
  message: '<script>문구</script>',
  questions: [],
  result: null,
  error: { code: 'invalid_input', message: '지원하지 않는 요청', retryable: false },
}
afterEach(() => vi.unstubAllGlobals())
describe('Python 응답 계약', () => {
  it('차단 메시지는 그대로 보존한다', () => expect(parseReply(reply)).toEqual(reply))
  it.each([
    {},
    { ...reply, mode: 'mock' },
    { ...reply, questions: [1] },
    { ...reply, result: { status: 'success', routes: [{}], unassigned_orders: [] } },
  ])('잘못된 응답을 거부한다', (value) => expect(() => parseReply(value)).toThrow())
  it('서버 오류에 요청을 자동 재전송하지 않는다', async () => {
    const request = vi.fn().mockResolvedValue(new Response('', { status: 503 }))
    vi.stubGlobal('fetch', request)
    await expect(sendAgentMessage('배차', 'thread')).rejects.toThrow('HTTP 503')
    expect(request).toHaveBeenCalledTimes(1)
    expect(JSON.parse(request.mock.calls[0]![1].body)).toEqual({
      message: '배차',
      thread_id: 'thread',
    })
  })
})
