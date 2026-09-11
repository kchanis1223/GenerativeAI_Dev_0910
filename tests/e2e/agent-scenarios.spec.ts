import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page, request }) => {
  test.skip(process.env.AGENT_SCENARIOS !== '1', 'Python --scenarios 서버가 필요한 시연 검증')
  expect(await (await request.get('/api/agent/health')).json()).toMatchObject({
    mode: 'offline',
    scenarios: true,
  })
  await page.goto('/workspace')
  await expect(page.getByRole('button', { name: 'M01 정상 배차', exact: true })).toBeVisible()
})

test('M01 대화 → 선택 자동화 → 배차 표와 지도', async ({ page }) => {
  await page.getByRole('button', { name: 'M01 정상 배차', exact: true }).click()
  await expect(page.locator('.map-legend button')).toHaveCount(4)
  await expect(page.locator('.summary-table tbody tr')).toHaveCount(5)
  await expect(page.locator('.order-list input:checked')).toHaveCount(6)
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(4)
  await expect(page.locator('.delivery-pin')).toHaveCount(6)
  await expect(page.locator('.summary-table')).toContainText('미제공')
  await page.getByRole('button', { name: '배송 순서 보기', exact: true }).click()
  await expect(page.locator('#delivery-details')).toContainText('활광어')
})

test('M02 배송일만 답하면 같은 요청으로 지도 표시', async ({ page }) => {
  await page.getByRole('button', { name: 'M02 배송일 누락', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('배송일을 알려주세요')
  await expect(page.locator('.map-legend button')).toHaveCount(0)
  await page.getByRole('button', { name: '2026-09-11로 배차', exact: true }).click()
  await expect(page.locator('.map-legend button')).toHaveCount(4)
})

test('M03 주소 확정 전 중단, 확인 후 표시, 새 요청은 다시 확인', async ({ page }) => {
  await page.getByRole('button', { name: 'M03 주소 확인', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('배차 호출 0회')
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(0)
  await page
    .getByRole('button', { name: '서울특별시 마포구 월드컵로 212 정문 확인', exact: true })
    .click()
  await expect(page.locator('.map-legend button')).toHaveCount(4)
  await page.getByRole('button', { name: 'M03 주소 확인', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('배차 호출 0회')
  await expect(page.locator('.map-legend button')).toHaveCount(0)
})

test('M04 부적합 차량이면 배차 호출과 경로가 없다', async ({ page }) => {
  await page.getByRole('button', { name: 'M04 부적합 차량', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('보관유형·적재량')
  await expect(page.getByRole('log')).toContainText('배차 호출 0회')
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(0)
})

test('M05 조회 제한 후 오류를 보존하고 배차는 한 번만 실행', async ({ page }) => {
  await page.getByRole('button', { name: 'M05 조회 시간 초과', exact: true }).click()
  await expect(page.getByRole('log')).toContainText(
    '배차 호출 1회 · 결과 조회 6회 · 통신 재시도 3회',
  )
  await expect(page.getByRole('log')).toContainText('timeout')
  await expect(page.getByRole('button', { name: '메시지 전송', exact: true })).toBeDisabled()
  await expect(page.locator('.map-legend button')).toHaveCount(0)
})

test('M06 미배정·ETA 없음, 배정된 경로만 표시', async ({ page }) => {
  await page.getByRole('button', { name: 'M06 일부 미배정', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('일부 미배정')
  await expect(page.locator('.map-legend button')).toHaveCount(3)
  await expect(page.locator('.unassigned')).toContainText('미배차 1건')
  await expect(page.locator('.summary-table')).toContainText('미제공')
})

test('M07 API 키 요구 차단, 대화의 값 마스킹', async ({ page }) => {
  await page.getByRole('button', { name: 'M07 API 키 요구', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('배차 호출 0회')
  await expect(page.getByRole('log')).toContainText('appKey=***')
  await expect(page.locator('body')).not.toContainText('demo-secret')
  await expect(page.locator('.map-legend button')).toHaveCount(0)
})

test('M08 서버 전용 Tool 인자는 실제 검증 계층에서 차단', async ({ page }) => {
  await page.getByRole('button', { name: 'M08 금지 Tool 인자', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('허용되지 않은 Tool 또는 인자를 차단')
  await expect(page.getByRole('log')).toContainText('배차 호출 0회')
  await expect(page.locator('.map-legend button')).toHaveCount(0)
})
