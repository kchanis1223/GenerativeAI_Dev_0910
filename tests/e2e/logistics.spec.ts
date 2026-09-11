import { expect, test } from '@playwright/test'

test('API 탐색으로 일괄 등록하고 목록과 오류 응답을 확인한다', async ({ page }) => {
  await page.goto('/workspace/api')
  await expect(page.getByLabel('API 선택').locator('option')).toHaveCount(24)
  await page.getByLabel('API 선택').selectOption('/orderListInsert')
  await page.getByRole('button', { name: '목업 실행', exact: true }).click()
  await expect(page.locator('.api-response')).toContainText('"resultCode": "200"')
  await page.getByLabel('API 선택').selectOption('/orderList')
  await page.getByRole('button', { name: '목업 실행', exact: true }).click()
  await expect(page.locator('.api-response')).toContainText('"resultCount": 10')
  await page.getByLabel('응답 시나리오').selectOption('unauthorized')
  await page.getByRole('button', { name: '목업 실행', exact: true }).click()
  await expect(page.locator('.api-response')).toContainText('"resultCode": "401"')
  await page.getByRole('button', { name: '주문 관리', exact: true }).click()
  await expect(page.locator('.tms-records > li')).toHaveCount(10)
  await page.getByRole('button', { name: '실행 기록', exact: true }).click()
  await expect(page.locator('.tms-history details')).toHaveCount(3)
})

test('로고 클릭 시 바다 전환을 거쳐 입장하고 시작하기 버튼은 없다', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('시작하기', { exact: true })).toHaveCount(0)
  await page.getByRole('link', { name: '바다로 워크스페이스 입장' }).click()
  await expect(page.locator('.ocean-transition')).toBeVisible()
  await page.screenshot({ path: 'test-results/ocean-transition.png' })
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.locator('.ocean-transition')).toHaveCount(0)
})
