import { test, expect } from '@playwright/test'

test('실제 센터를 조회하고 목업 배차 센터를 유지한다', async ({ page }) => {
  await page.route('**/api/tms/centerList', (route) =>
    route.fulfill({
      json: {
        resultCode: '200',
        resultCount: 1,
        resultMessage: 'success',
        resultData: [
          {
            centerId: 'live-1',
            centerName: '실제 테스트 센터',
            address: '서울특별시 테스트 주소',
            latitude: 37.5,
            longitude: 127,
            seq: 1,
            updateDate: '20260911',
          },
        ],
      },
    }),
  )
  await page.goto('/workspace')
  await page.getByRole('button', { name: '실제 센터 조회', exact: true }).click()
  await expect(page.getByRole('list', { name: '실제 TMS 센터 조회 결과' })).toContainText(
    '실제 테스트 센터',
  )
  await expect(page.locator('.center-option.chosen')).toContainText('노량진센터')
  await expect(page.locator('#vehicle-label')).toContainText('5 / 5대')
})

test('키 누락 안내 후 재조회로 빈 목록을 확인한다', async ({ page }) => {
  await page.route('**/api/tms/centerList', (route) =>
    route.fulfill({ status: 503, json: { code: 'TMS_KEY_MISSING' } }),
  )
  await page.goto('/workspace')
  await page.getByRole('button', { name: '실제 센터 조회', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('TMAP_APP_KEY')
  await page.route('**/api/tms/centerList', (route) =>
    route.fulfill({
      json: {
        resultCode: '200',
        resultCount: 0,
        resultMessage: 'success',
        resultData: [],
      },
    }),
  )
  await page.getByRole('button', { name: '실제 센터 조회', exact: true }).click()
  await expect(page.getByText('등록된 센터가 없습니다.', { exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})
