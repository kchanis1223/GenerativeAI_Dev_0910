import { expect, test } from '@playwright/test'
import { mockCenters } from '../../src/data/centers'

async function ready(page: import('@playwright/test').Page) {
  await page.goto('/workspace/centers')
  await expect(page.getByText('정상 완료', { exact: true })).toBeVisible()
}

test('조회, 상세 선택, 검색, 내보내기와 실행 기록', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await ready(page)
  await expect(page.locator('.center-table tbody tr')).toHaveCount(8)
  await page.getByRole('button', { name: '성수센터 상세 보기' }).click()
  await expect(page.locator('.detail-name h3')).toHaveText('성수센터')
  await page.getByRole('button', { name: '강남센터 선택', exact: true }).click()
  await expect(page.locator('.detail-name h3')).toHaveText('강남센터')
  await page.getByRole('searchbox', { name: '센터 검색' }).fill('강남')
  await page.getByRole('button', { name: '조회 실행', exact: true }).click()
  await expect(page.locator('.center-table tbody tr')).toHaveCount(1)
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'JSON 내보내기' }).click()
  expect((await downloadPromise).suggestedFilename()).toBe('tms-centers.json')
  await page.getByRole('button', { name: '실행 기록', exact: true }).click()
  await expect(page.locator('.history-table tbody tr')).toHaveCount(2)
  expect(errors).toEqual([])
})

test('지역 필터와 빈 결과를 표시한다', async ({ page }) => {
  await ready(page)
  await page.getByLabel('지역', { exact: true }).selectOption('경기도')
  await page.getByRole('button', { name: '조회 실행', exact: true }).click()
  await expect(page.locator('.center-table tbody tr')).toHaveCount(2)
  await page.getByRole('searchbox').fill('없는센터')
  await page.getByRole('button', { name: '조회 실행', exact: true }).click()
  await expect(page.getByText('조회된 센터가 없습니다', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '조건 초기화' }).click()
  await expect(page.locator('.center-table tbody tr')).toHaveCount(8)
})

test('오류 시나리오별로 올바른 단계에서 멈추고 복구한다', async ({ page }) => {
  await ready(page)
  for (const [scenario, step] of [
    ['unauthorized', 'API 호출'],
    ['timeout', 'API 호출'],
    ['invalid', '응답 검증'],
  ]) {
    await page.getByLabel('테스트 시나리오').selectOption(scenario!)
    await page.getByRole('button', { name: '조회 실행', exact: true }).click()
    await expect(page.locator('.error-banner')).toBeVisible()
    await expect(page.locator('.flow-steps li.error strong')).toHaveText(step!)
    await expect(page.locator('.center-table tbody tr')).toHaveCount(0)
  }
  await page.getByLabel('테스트 시나리오').selectOption('empty')
  await page.getByRole('button', { name: '조회 실행', exact: true }).click()
  await expect(page.getByText('조회된 센터가 없습니다', { exact: true })).toBeVisible()
  await expect(page.locator('.flow-steps li.success')).toHaveCount(5)
  await page.getByLabel('테스트 시나리오').selectOption('success')
  await page.getByRole('button', { name: '조회 실행', exact: true }).click()
  await expect(page.locator('.center-table tbody tr')).toHaveCount(8)
})

test('흐름 화면에서 원본 응답을 확인한다', async ({ page }) => {
  await ready(page)
  await page.getByRole('button', { name: '동작 흐름', exact: true }).click()
  await page.getByRole('button', { name: '원본 응답 JSON' }).click()
  await expect(page.locator('.response-json')).toContainText('"resultCode": "200"')
  await expect(page.locator('.response-json')).toContainText('euljiro_center')
})

test('설정 검증과 프록시 응답을 실제 UI 경로로 처리한다', async ({ page }) => {
  await ready(page)
  await page.getByRole('button', { name: '연결 설정', exact: true }).first().click()
  await page.getByRole('radio', { name: /실제 API/ }).check()
  await page.getByLabel('프록시 경로').fill('https://example.com')
  await page.getByRole('button', { name: '설정 적용' }).click()
  await expect(page.getByRole('alert')).toContainText('/api/')
  await page.getByLabel('프록시 경로').fill('/api/tms/centerList')
  await page.route('**/api/tms/centerList', (route) =>
    route.fulfill({
      json: {
        resultCode: '200',
        resultCount: 1,
        resultMessage: 'success',
        resultData: [mockCenters[0]],
      },
    }),
  )
  await page.getByRole('button', { name: '설정 적용' }).click()
  await page.getByRole('button', { name: '조회 실행', exact: true }).click()
  await expect(page.locator('.center-table tbody tr')).toHaveCount(1)
  await expect(page.getByText('프록시 연결 모드', { exact: true }).first()).toBeVisible()
})

test('모바일 레이아웃과 키보드로 설정 닫기', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await ready(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.getByRole('button', { name: '연결 설정', exact: true }).first().click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await page.getByRole('button', { name: '동작 흐름', exact: true }).click()
  await expect(page.getByRole('heading', { name: '눈으로 확인하는 동작 흐름' })).toBeVisible()
})

test('구간 이동과 실행 상태 필터가 조회 결과에 맞게 작동한다', async ({ page }) => {
  await ready(page)
  await page.getByRole('link', { name: '센터 상세', exact: true }).click()
  await expect(page.locator('#center-detail')).toBeFocused()
  await expect(page.getByRole('link', { name: '센터 상세', exact: true })).toHaveAttribute(
    'aria-current',
    'location',
  )
  await page.getByRole('link', { name: '조회 조건', exact: true }).click()
  await expect(page.locator('#lookup')).toBeFocused()
  await page.getByRole('button', { name: '실행 기록', exact: true }).click()
  await page.locator('.history-filters').getByRole('button', { name: '실패', exact: true }).click()
  await expect(page.locator('.history-table tbody tr')).toHaveCount(0)
  await expect(page.getByText('조건에 맞는 실행 기록이 없습니다.', { exact: true })).toBeVisible()
  await page.locator('.history-filters').getByRole('button', { name: '완료', exact: true }).click()
  await expect(page.locator('.history-table tbody tr')).toHaveCount(1)
})
