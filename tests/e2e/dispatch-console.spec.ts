import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('https://tile.openstreetmap.org/**', (route) =>
    route.fulfill({
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#edf3f2"/><path d="M0 128H256M128 0V256" stroke="#fff" stroke-width="3"/></svg>',
    }),
  )
  await page.clock.install({ time: new Date('2026-09-11T00:00:00Z') })
  await page.goto('/workspace')
})

test('기본 화면에 데이터 선택, 빈 결과, 지도가 있고 기존 주소도 같은 화면으로 연결된다', async ({
  page,
}) => {
  await expect(page.getByRole('heading', { name: '배송 배차', exact: true })).toBeVisible()
  await expect(page.locator('#order-label')).toContainText('20곳 · 40건')
  await expect(page.locator('#vehicle-label')).toContainText('5 / 5대')
  await expect(page.locator('.weight-summary')).toContainText('3,125 kg')
  await expect(page.getByRole('table', { name: '차량별 배차 결과' })).toContainText(
    '배차를 요청하면',
  )
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(20)
  await expect(page.locator('.center-pin')).toHaveCount(1)
  await expect(page.getByRole('link', { name: 'OpenStreetMap' })).toBeVisible()
  await page.goto('/workspace/vehicles')
  await expect(page).toHaveURL('/workspace')
  await expect(page.getByRole('heading', { name: '배송 배차', exact: true })).toBeVisible()
})

test('배차 모달에서 결과로 전환하고 차량별 경로와 배송 순서를 확인한다', async ({ page }) => {
  await page.getByRole('button', { name: '배차 요청', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('table')).toContainText('20 곳 / 40 건')
  await expect(page.getByRole('checkbox', { name: '센터로 복귀', exact: true })).toBeDisabled()
  await page.clock.runFor(2400)
  await expect(dialog).not.toBeVisible()
  await expect(page.locator('.result-state')).toContainText('5대 · 40건 배정')
  await expect(page.locator('.summary-table tbody tr')).toHaveCount(6)
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(5)
  await page.getByTitle('바다로 냉장차 1호 · 배송 1', { exact: true }).dispatchEvent('click')
  await expect(page.locator('.leaflet-popup-content')).toContainText('바다로 냉장차 1호')
  await expect(page.locator('.detail-bar')).toContainText('바다로 냉장차 1호')
  await page.locator('.vehicle-link').filter({ hasText: '바다로 냉장차 2호' }).click()
  await expect(page.getByRole('table', { name: '바다로 냉장차 2호 배송 순서' })).toBeVisible()
  await expect(page.locator('.detail-table tbody tr')).toHaveCount(10)
  await expect(page.locator('.detail-table')).toContainText('냉동')
  await page.getByRole('button', { name: '경로 숨기기', exact: true }).click()
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(0)
  await expect(page.locator('.delivery-pin')).toHaveCount(0)
  await expect(page.locator('.center-pin')).toHaveCount(1)
  await page.getByRole('checkbox', { name: '바다로 냉장차 2호 경로 표시', exact: true }).check()
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(1)
  await page.getByRole('button', { name: '경로 모두 보기', exact: true }).click()
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(5)
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: '배차 결과 다운로드' }).click()
  expect((await download).suggestedFilename()).toBe('badaro-2026-09-11.json')
  await page.getByRole('checkbox', { name: '센터로 복귀', exact: true }).uncheck()
  await expect(page.locator('.empty-result')).toBeVisible()
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(20)
})

test('배차 창 닫기와 계산 취소를 구분하고 재요청할 수 있다', async ({ page }) => {
  await page.getByRole('button', { name: '배차 요청', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: '닫기', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByRole('button', { name: '배차 진행 보기', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '배차 진행 보기', exact: true }).click()
  await page.getByRole('button', { name: '배차 취소', exact: true }).click()
  await page.clock.runFor(2400)
  await expect(page.locator('.result-state')).toHaveText('배차 대기')
  await page.getByRole('button', { name: '배차 요청', exact: true }).click()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await page.clock.runFor(2400)
  await expect(page.locator('.result-state')).toContainText('40건 배정')
})

test('빈 선택을 막고 운송 가능한 차량이 없으면 미배차 사유를 표시한다', async ({ page }) => {
  const vehicles = page.locator('.selection-panel').filter({ has: page.locator('#vehicle-label') })
  await vehicles.getByRole('checkbox', { name: '전체 선택', exact: true }).uncheck()
  await expect(page.getByRole('button', { name: '배차 요청', exact: true })).toBeDisabled()
  await vehicles.getByRole('checkbox', { name: '바다로 냉장차 1호', exact: true }).check()
  const orders = page.locator('.selection-panel').filter({ has: page.locator('#order-label') })
  await orders.getByRole('checkbox', { name: '전체 선택', exact: true }).uncheck()
  await expect(page.getByRole('button', { name: '배차 요청', exact: true })).toBeDisabled()
  await page.getByRole('combobox', { name: '배송 품목 필터' }).selectOption('냉동')
  await orders.getByRole('checkbox', { name: '전체 선택', exact: true }).check()
  await expect(page.locator('#order-label')).toContainText('10곳 · 10건')
  await page.getByRole('button', { name: '배차 요청', exact: true }).click()
  await page.clock.runFor(2400)
  await expect(page.locator('.unassigned summary')).toContainText('미배차 10건')
  await expect(page.locator('.unassigned li')).toHaveCount(10)
  await expect(page.locator('.unassigned li').first()).toContainText(
    '품목을 운송할 수 있는 차량이 없습니다.',
  )
})

test('모바일에서 결과를 접고 펼칠 수 있으며 문서가 가로로 넘치지 않는다', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('button', { name: '배차 요청', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '배차 요청', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.clock.runFor(2400)
  await page.locator('.vehicle-link').first().click()
  await expect(page.locator('.detail-table')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: '배차 결과 접기', exact: true }).click()
  await expect(page.locator('#results-content')).not.toBeVisible()
  await expect(page.getByRole('region', { name: '배송 경로 지도' })).toBeVisible()
  await page.getByRole('button', { name: '배차 결과 펼치기', exact: true }).click()
  await expect(page.locator('#results-content')).toBeVisible()
})

test('배경 지도 요청 실패를 안내하면서 배송 위치는 유지한다', async ({ page }) => {
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  await page.reload()
  await expect(page.locator('.map-error')).toBeVisible()
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(20)
})

test('데스크톱은 왼쪽 선택·결과와 오른쪽 큰 지도로 나뉘며 왼쪽 스크롤이 지도 크기를 바꾸지 않는다', async ({
  page,
}) => {
  const panel = page.locator('.control-panel')
  const map = page.locator('.map-region')
  const left = (await panel.boundingBox())!
  const right = (await map.boundingBox())!
  expect(right.x).toBeGreaterThanOrEqual(left.x + left.width - 1)
  expect(right.y).toBe(left.y)
  expect(right.width).toBeGreaterThan(left.width)
  expect(right.height).toBeGreaterThan(800)
  await page.getByRole('button', { name: '배차 요청', exact: true }).click()
  await page.clock.runFor(2400)
  await page.locator('.vehicle-link').first().click()
  await expect(page.locator('.detail-table')).toBeVisible()
  const after = (await map.boundingBox())!
  expect(after).toEqual(right)
  expect(await panel.evaluate((el) => el.scrollTop)).toBeGreaterThan(0)
  expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(1050)
})
