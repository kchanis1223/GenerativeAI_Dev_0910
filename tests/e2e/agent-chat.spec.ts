import { test, expect } from '@playwright/test'

const reply = {
  thread_id: 'a667febe-4f25-4b82-a7ee-245ce837624e',
  request_id: 'request-1',
  mode: 'offline',
  status: 'needs_clarification',
  message: '배송일을 알려주세요.',
  questions: ['배송일은 언제인가요?'],
  result: null,
  error: null,
}
test('재질문에 같은 대화 ID로 답하고 부분 배차와 누락값을 표시한다', async ({ page }) => {
  await page.route('**/api/agent/health', (r) =>
    r.fulfill({ json: { status: 'ok', mode: 'offline' } }),
  )
  const bodies: Record<string, unknown>[] = []
  await page.route('**/api/agent/chat', async (r) => {
    bodies.push(r.request().postDataJSON())
    await r.fulfill({
      json:
        bodies.length === 1
          ? reply
          : {
              ...reply,
              status: 'completed',
              questions: [],
              message: '일부 배차됐습니다.',
              map_data: {
                origin: { lat: 37.5, lon: 126.9, matched_address: '출발지' },
                stops: { 'order-1': { lat: 37.6, lon: 127, matched_address: '서버 확정 배송지' } },
              },
              result: {
                status: 'partial',
                routes: [
                  {
                    vehicle_id: 'LIVE01',
                    stops: [{ sequence: 1, order_id: 'order-1', destination_id: 'S01', eta: null }],
                    distance_meters: null,
                    estimated_duration_seconds: null,
                  },
                ],
                unassigned_orders: [
                  { order_id: 'order-2', reason_code: 'capacity', reason_message: '적재량 초과' },
                ],
              },
            },
    })
  })
  await page.goto('/workspace')
  const chat = page.locator('.agent-chat')
  await expect(chat).toContainText('Python 합성 Mock')
  await page.getByLabel('에이전트 메시지').fill('마포 배차해줘')
  await page.getByRole('button', { name: '메시지 전송', exact: true }).click()
  await expect(chat).toContainText('배송일은 언제인가요?')
  await page.getByLabel('에이전트 메시지').fill('2026-09-11')
  await page.getByRole('button', { name: '메시지 전송', exact: true }).click()
  await expect(chat).toContainText('일부 배차')
  await expect(chat).toContainText('적재량 초과')
  await expect(chat).toContainText('거리 미제공')
  await expect(page.locator('.delivery-pin')).toHaveCount(1)
  await expect(page.locator('.leaflet-overlay-pane path[stroke-dasharray="8 5"]')).toHaveCount(1)
  await page.locator('.delivery-pin').click()
  await expect(page.locator('.leaflet-popup')).toContainText('서버 확정 배송지')
  await expect(page.locator('.map-disclaimer')).toContainText('확정 좌표')
  await page.getByRole('button', { name: '목업 데이터', exact: true }).click()
  await expect(page.locator('.delivery-pin')).toHaveCount(0)
  await page.getByRole('button', { name: '에이전트 결과', exact: true }).click()
  await expect(page.locator('.delivery-pin')).toHaveCount(1)
  expect(bodies).toEqual([
    { message: '마포 배차해줘' },
    { message: '2026-09-11', thread_id: reply.thread_id },
  ])
  await expect(page.getByLabel('에이전트 메시지')).toBeDisabled()
  await page.getByRole('button', { name: '새 대화', exact: true }).click()
  await expect(page.locator('.delivery-pin')).toHaveCount(0)
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(0)
  await page.getByLabel('에이전트 메시지').fill('새 요청')
  await page.getByRole('button', { name: '메시지 전송', exact: true }).click()
  await expect.poll(() => bodies.length).toBe(3)
  expect(bodies[2]).toEqual({ message: '새 요청' })
})

test('응답 유실 시 중복 배차를 자동 재전송하지 않는다', async ({ page }) => {
  await page.route('**/api/agent/health', (r) =>
    r.fulfill({ json: { status: 'ok', mode: 'offline' } }),
  )
  let calls = 0
  await page.route('**/api/agent/chat', (r) => {
    calls++
    return r.abort()
  })
  await page.goto('/workspace')
  await expect(page.locator('.chat-status')).toContainText('Python 합성 Mock')
  await page.getByLabel('에이전트 메시지').fill('배차해줘')
  await page.getByRole('button', { name: '메시지 전송', exact: true }).click()
  await expect(page.locator('.agent-chat [role=alert]')).toContainText('자동 재전송하지 않습니다')
  await expect(page.getByRole('button', { name: '메시지 전송', exact: true })).toBeDisabled()
  expect(calls).toBe(1)
})

test('Vue에서 Python offline 서버로 재질문과 배차 결과를 받는다', async ({ page, request }) => {
  test.skip(
    process.env.AGENT_INTEGRATION !== '1',
    'Python offline 서버를 실행한 후 AGENT_INTEGRATION=1로 검증',
  )
  const health = await request.get('/api/agent/health')
  expect(await health.json()).toEqual({ status: 'ok', mode: 'offline' })
  await page.goto('/workspace')
  await expect(page.locator('.chat-status')).toContainText('Python 합성 Mock')
  await page.getByLabel('에이전트 메시지').fill('마포 서대문 은평 배차해줘')
  await page.getByRole('button', { name: '메시지 전송', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('배송일')
  await page.getByLabel('에이전트 메시지').fill('2026-09-11')
  await page.getByRole('button', { name: '메시지 전송', exact: true }).click()
  const result = page.getByRole('region', { name: 'Python 배차 결과' })
  await expect(result).toContainText('배차 성공')
  await expect(result.locator('tbody tr')).toHaveCount(6)
  await expect(result).toContainText('미배정 0건')
  await expect(result).toContainText('거리 미제공')
})
